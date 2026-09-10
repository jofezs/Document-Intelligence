import shutil
from pathlib import Path
from typing import Callable

import pymupdf

from app.config import settings


class EditError(Exception):
    """Raised for invalid edit requests (bad page number, text not found, ...)."""


def _doc_dir(doc_id: str) -> Path:
    return settings.storage_dir / doc_id


def source_path(doc_id: str) -> Path:
    return _doc_dir(doc_id) / "source.pdf"


def working_path(doc_id: str) -> Path:
    return _doc_dir(doc_id) / "working.pdf"


def active_path(doc_id: str) -> Path:
    """The PDF that reflects the document's current state: the working copy
    if any edits have been made, otherwise the original upload."""
    working = working_path(doc_id)
    return working if working.exists() else source_path(doc_id)


def reset_document(doc_id: str) -> None:
    working = working_path(doc_id)
    if working.exists():
        working.unlink()


def _ensure_working_copy(doc_id: str) -> Path:
    working = working_path(doc_id)
    if not working.exists():
        shutil.copyfile(active_path(doc_id), working)
    return working


def _mutate(doc_id: str, mutator: Callable[[pymupdf.Document], None]) -> None:
    """Open the working copy, apply `mutator(doc)`, and atomically save the
    result back. If `mutator` raises, the working copy is left untouched."""
    path = _ensure_working_copy(doc_id)
    doc = pymupdf.open(path)
    try:
        mutator(doc)
        tmp_path = path.with_name(path.name + ".tmp")
        doc.save(tmp_path, garbage=4, deflate=True)
    finally:
        doc.close()
    tmp_path.replace(path)


def _require_page(doc: pymupdf.Document, page_number: int) -> pymupdf.Page:
    if not (1 <= page_number <= doc.page_count):
        raise EditError(f"Page {page_number} does not exist (document has {doc.page_count} pages)")
    return doc[page_number - 1]


def highlight_text(
    doc_id: str, page_number: int, text: str, color: tuple[float, float, float] = (1, 1, 0)
) -> int:
    match_count = 0

    def mutator(doc: pymupdf.Document) -> None:
        nonlocal match_count
        page = _require_page(doc, page_number)
        quads = page.search_for(text, quads=True)
        if not quads:
            raise EditError(f"Text not found on page {page_number}")
        annot = page.add_highlight_annot(quads)
        annot.set_colors(stroke=color)
        annot.update()
        match_count = len(quads)

    _mutate(doc_id, mutator)
    return match_count


def add_note(doc_id: str, page_number: int, x: float, y: float, text: str) -> None:
    def mutator(doc: pymupdf.Document) -> None:
        page = _require_page(doc, page_number)
        annot = page.add_text_annot((x, y), text)
        annot.update()

    _mutate(doc_id, mutator)


def redact_text(doc_id: str, text: str, page_number: int | None = None) -> int:
    match_count = 0

    def mutator(doc: pymupdf.Document) -> None:
        nonlocal match_count
        pages = [_require_page(doc, page_number)] if page_number is not None else list(doc)
        for page in pages:
            rects = page.search_for(text)
            for rect in rects:
                page.add_redact_annot(rect, fill=(0, 0, 0))
            match_count += len(rects)
            if rects:
                page.apply_redactions()
        if match_count == 0:
            raise EditError("Text not found")

    _mutate(doc_id, mutator)
    return match_count


def delete_page(doc_id: str, page_number: int) -> int:
    remaining = 0

    def mutator(doc: pymupdf.Document) -> None:
        nonlocal remaining
        _require_page(doc, page_number)
        if doc.page_count == 1:
            raise EditError("Cannot delete the only page in the document")
        doc.delete_page(page_number - 1)
        remaining = doc.page_count

    _mutate(doc_id, mutator)
    return remaining


def rotate_page(doc_id: str, page_number: int, degrees: int) -> None:
    if degrees % 90 != 0:
        raise EditError("degrees must be a multiple of 90")

    def mutator(doc: pymupdf.Document) -> None:
        page = _require_page(doc, page_number)
        page.set_rotation((page.rotation + degrees) % 360)

    _mutate(doc_id, mutator)


def reorder_pages(doc_id: str, order: list[int]) -> None:
    def mutator(doc: pymupdf.Document) -> None:
        if sorted(order) != list(range(1, doc.page_count + 1)):
            raise EditError("order must be a permutation of all current page numbers")
        doc.select([p - 1 for p in order])

    _mutate(doc_id, mutator)


def list_form_fields(doc_id: str) -> list[dict]:
    fields: list[dict] = []
    with pymupdf.open(active_path(doc_id)) as doc:
        for page_index in range(doc.page_count):
            page = doc[page_index]
            for widget in page.widgets() or []:
                fields.append(
                    {
                        "name": widget.field_name,
                        "type": widget.field_type_string,
                        "page_number": page_index + 1,
                        "value": widget.field_value,
                        "choices": widget.choice_values or None,
                    }
                )
    return fields


def fill_form_fields(doc_id: str, values: dict[str, str]) -> int:
    updated = 0

    def mutator(doc: pymupdf.Document) -> None:
        nonlocal updated
        for page in doc:
            for widget in page.widgets() or []:
                if widget.field_name in values:
                    widget.field_value = values[widget.field_name]
                    widget.update()
                    updated += 1
        if updated == 0:
            raise EditError("No matching form fields found")

    _mutate(doc_id, mutator)
    return updated
