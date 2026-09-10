import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import settings
from app.models import DocumentOut
from app.services import pdf_processor, store, vector_store
from app.services import embeddings as embeddings_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _doc_dir(doc_id: str) -> Path:
    return settings.storage_dir / doc_id


def _process_document(doc_id: str, pdf_path: Path) -> None:
    doc = store.get_document(doc_id)
    if doc is None:
        return
    try:
        pages = pdf_processor.render_and_extract(pdf_path, _doc_dir(doc_id) / "pages")

        ids: list[str] = []
        embeds: list[list[float]] = []
        documents: list[str] = []
        metadatas: list[dict] = []

        for page in pages:
            for chunk in pdf_processor.chunk_text(page.text, page.page_number):
                chunk_id = f"{doc_id}_p{chunk.page_number}_c{chunk.chunk_index}"
                ids.append(chunk_id)
                embeds.append(embeddings_service.embed_text(chunk.text))
                documents.append(chunk.text)
                metadatas.append(
                    {
                        "doc_id": doc_id,
                        "doc_name": doc["filename"],
                        "page_number": chunk.page_number,
                    }
                )

        if ids:
            vector_store.add_chunks(ids, embeds, documents, metadatas)

        doc["status"] = "ready"
        doc["num_pages"] = len(pages)
        store.upsert_document(doc)
    except Exception as exc:  # noqa: BLE001 - surface any processing failure to the UI
        doc["status"] = "error"
        doc["error"] = str(exc)
        store.upsert_document(doc)


@router.post("", response_model=DocumentOut)
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    doc_id = str(uuid.uuid4())
    doc_dir = _doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = doc_dir / "source.pdf"
    with open(pdf_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    doc = {
        "id": doc_id,
        "filename": file.filename,
        "status": "processing",
        "num_pages": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store.upsert_document(doc)

    background_tasks.add_task(_process_document, doc_id, pdf_path)
    return doc


@router.get("", response_model=list[DocumentOut])
async def list_documents():
    return sorted(store.list_documents(), key=lambda d: d["created_at"], reverse=True)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    doc = store.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    vector_store.delete_document(doc_id)
    store.delete_document(doc_id)
    shutil.rmtree(_doc_dir(doc_id), ignore_errors=True)
    return {"status": "deleted"}


@router.get("/{doc_id}/pages/{page_number}/image")
async def get_page_image(doc_id: str, page_number: int):
    image_path = _doc_dir(doc_id) / "pages" / f"page_{page_number}.png"
    if not image_path.exists():
        raise HTTPException(404, "Page image not found")
    return FileResponse(image_path, media_type="image/png")
