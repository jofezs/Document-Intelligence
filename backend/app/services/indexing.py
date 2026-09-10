from pathlib import Path

from app.config import settings
from app.services import embeddings as embeddings_service
from app.services import pdf_processor, store, vector_store


def _images_dir(doc_id: str) -> Path:
    return settings.storage_dir / doc_id / "pages"


def render_only(doc_id: str, pdf_path: Path) -> int:
    """Re-render page images without touching the vector index. Used after
    cosmetic edits (highlight, note, rotate) where the underlying text is
    unchanged."""
    pages = pdf_processor.render_and_extract(pdf_path, _images_dir(doc_id))
    return len(pages)


def index_document(doc_id: str, pdf_path: Path) -> int:
    """Render pages, chunk text, embed, and replace this document's vector
    store entries. Used both for the initial upload and for re-indexing after
    a content-changing edit (redact, delete/reorder pages, fill form)."""
    doc = store.get_document(doc_id)
    if doc is None:
        raise ValueError(f"Unknown document: {doc_id}")

    pages = pdf_processor.render_and_extract(pdf_path, _images_dir(doc_id))

    vector_store.delete_document(doc_id)

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

    doc["num_pages"] = len(pages)
    store.upsert_document(doc)
    return len(pages)
