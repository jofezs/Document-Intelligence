from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services import indexing, pdf_editor, store

router = APIRouter(prefix="/api/documents/{doc_id}", tags=["edit"])


def _require_document(doc_id: str) -> dict:
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


def _reindex_visual(doc_id: str) -> None:
    """Re-render page images only — for edits that don't change extractable text."""
    indexing.render_only(doc_id, pdf_editor.active_path(doc_id))


def _reindex_full(doc_id: str) -> None:
    """Re-render pages and rebuild the vector index — for edits that change
    extractable text or page numbering."""
    indexing.index_document(doc_id, pdf_editor.active_path(doc_id))


class HighlightRequest(BaseModel):
    page_number: int
    text: str
    color: tuple[float, float, float] = (1, 1, 0)


class NoteRequest(BaseModel):
    page_number: int
    x: float
    y: float
    text: str


class StampRequest(BaseModel):
    page_number: int
    x: float
    y: float
    text: str
    fontsize: float = 11


class RedactRequest(BaseModel):
    text: str
    page_number: Optional[int] = None


class RotateRequest(BaseModel):
    degrees: int


class ReorderRequest(BaseModel):
    order: list[int]


class FormFillRequest(BaseModel):
    values: dict[str, str]


@router.post("/highlight")
async def highlight(doc_id: str, payload: HighlightRequest):
    _require_document(doc_id)
    try:
        matches = pdf_editor.highlight_text(doc_id, payload.page_number, payload.text, payload.color)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_visual(doc_id)
    return {"matches": matches}


@router.post("/note")
async def add_note(doc_id: str, payload: NoteRequest):
    _require_document(doc_id)
    try:
        pdf_editor.add_note(doc_id, payload.page_number, payload.x, payload.y, payload.text)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_visual(doc_id)
    return {"status": "ok"}


@router.post("/stamp")
async def stamp_text(doc_id: str, payload: StampRequest):
    _require_document(doc_id)
    try:
        pdf_editor.stamp_text(doc_id, payload.page_number, payload.x, payload.y, payload.text, payload.fontsize)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    return {"status": "ok"}


@router.post("/redact")
async def redact(doc_id: str, payload: RedactRequest):
    _require_document(doc_id)
    try:
        matches = pdf_editor.redact_text(doc_id, payload.text, payload.page_number)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    return {"matches": matches}


@router.delete("/pages/{page_number}")
async def delete_page(doc_id: str, page_number: int):
    _require_document(doc_id)
    try:
        remaining = pdf_editor.delete_page(doc_id, page_number)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    return {"num_pages": remaining}


@router.post("/pages/{page_number}/rotate")
async def rotate_page(doc_id: str, page_number: int, payload: RotateRequest):
    _require_document(doc_id)
    try:
        pdf_editor.rotate_page(doc_id, page_number, payload.degrees)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_visual(doc_id)
    return {"status": "ok"}


@router.post("/pages/reorder")
async def reorder_pages(doc_id: str, payload: ReorderRequest):
    _require_document(doc_id)
    try:
        pdf_editor.reorder_pages(doc_id, payload.order)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    return {"status": "ok"}


@router.get("/form-fields")
async def get_form_fields(doc_id: str):
    _require_document(doc_id)
    return pdf_editor.list_form_fields(doc_id)


@router.post("/form-fields")
async def fill_form_fields(doc_id: str, payload: FormFillRequest):
    _require_document(doc_id)
    try:
        updated = pdf_editor.fill_form_fields(doc_id, payload.values)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    return {"updated": updated}


@router.get("/history")
async def get_history(doc_id: str):
    _require_document(doc_id)
    return {"count": pdf_editor.history_count(doc_id)}


@router.post("/undo")
async def undo(doc_id: str):
    _require_document(doc_id)
    try:
        pdf_editor.undo(doc_id)
    except pdf_editor.EditError as exc:
        raise HTTPException(400, str(exc)) from exc
    _reindex_full(doc_id)
    doc = store.get_document(doc_id)
    return {"count": pdf_editor.history_count(doc_id), "num_pages": doc["num_pages"]}


@router.post("/reset")
async def reset_document(doc_id: str):
    _require_document(doc_id)
    pdf_editor.reset_document(doc_id)
    _reindex_full(doc_id)
    return {"status": "reset"}


@router.get("/download")
async def download(doc_id: str):
    doc = _require_document(doc_id)
    return FileResponse(pdf_editor.active_path(doc_id), media_type="application/pdf", filename=doc["filename"])
