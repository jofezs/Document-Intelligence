import shutil
import time
from pathlib import Path
from typing import Callable

import pymupdf

from app.config import settings

_HISTORY_CAP = 15


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


def _history_dir(doc_id: str) -> Path:
    d = _doc_dir(doc_id) / "history"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _history_entries(doc_id: str) -> list[Path]:
    d = _doc_dir(doc_id) / "history"
    if not d.exists():
        return []
    return sorted(d.glob("*.pdf"), key=lambda p: int(p.stem))


def _push_history(doc_id: str, pre_mutation_path: Path) -> None:
    entries = _history_entries(doc_id)
    if len(entries) >= _HISTORY_CAP:
        entries[0].unlink()
    dest = _history_dir(doc_id) / f"{int(time.time() * 1000)}.pdf"
    shutil.copyfile(pre_mutation_path, dest)


def history_count(doc_id: str) -> int:
    return len(_history_entries(doc_id))


def undo(doc_id: str) -> None:
    entries = _history_entries(doc_id)
    if not entries:
        raise EditError("Nothing to undo")
    last = entries[-1]
    shutil.copyfile(last, working_path(doc_id))
    last.unlink()


def reset_document(doc_id: str) -> None:
    working = working_path(doc_id)
    if working.exists():
        working.unlink()
    history_dir = _doc_dir(doc_id) / "history"
    if history_dir.exists():
        shutil.rmtree(history_dir)


def _ensure_working_copy(doc_id: str) -> Path:
    working = working_path(doc_id)
    if not working.exists():
        shutil.copyfile(active_path(doc_id), working)
    return working


def _mutate(doc_id: str, mutator: Callable[[pymupdf.Document], None]) -> None:
    """Open the working copy, apply `mutator(doc)`, and atomically save the
    result back. If `mutator` raises, the working copy is left untouched and
    no history entry is recorded."""
    path = _ensure_working_copy(doc_id)
    doc = pymupdf.open(path)
    try:
        mutator(doc)
        tmp_path = path.with_name(path.name + ".tmp")
        doc.save(tmp_path, garbage=4, deflate=True)
    finally:
        doc.close()
    # Snapshot the pre-mutation content for undo now that we know the edit
    # succeeded, while `path` still holds it (we haven't replaced it yet).
    _push_history(doc_id, path)
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


def stamp_text(doc_id: str, page_number: int, x: float, y: float, text: str, fontsize: float = 11) -> None:
    """Burn visible text directly onto the page at (x, y) — e.g. filling in a
    blank on a flat (non-interactive) form. Unlike add_note, this becomes part
    of the page's extractable text."""

    def mutator(doc: pymupdf.Document) -> None:
        page = _require_page(doc, page_number)
        page.insert_text((x, y), text, fontsize=fontsize)

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
