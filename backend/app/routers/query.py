from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models import Citation, QueryRequest, QueryResponse
from app.services import embeddings as embeddings_service
from app.services import llm, vector_store

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("", response_model=QueryResponse)
async def query_documents(payload: QueryRequest):
    if not payload.question.strip():
        raise HTTPException(400, "Question must not be empty")

    query_embedding = embeddings_service.embed_text(payload.question)
    results = vector_store.query(
        query_embedding,
        n_results=payload.top_k or settings.max_context_chunks,
        doc_ids=payload.doc_ids,
    )

    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    documents = documents[0]
    metadatas = metadatas[0]

    if not documents:
        return QueryResponse(
            answer="I couldn't find any relevant content in the uploaded documents to answer that.",
            citations=[],
        )

    text_context: list[dict] = []
    citations: list[Citation] = []
    seen_pages: set[tuple[str, int]] = set()
    image_paths = []

    for text, meta in zip(documents, metadatas):
        text_context.append(
            {"doc_name": meta["doc_name"], "page_number": meta["page_number"], "text": text}
        )
        citations.append(
            Citation(
                doc_id=meta["doc_id"],
                doc_name=meta["doc_name"],
                page_number=meta["page_number"],
                snippet=text[:220],
                image_url=f"/api/documents/{meta['doc_id']}/pages/{meta['page_number']}/image",
            )
        )

        page_key = (meta["doc_id"], meta["page_number"])
        if page_key not in seen_pages and len(image_paths) < settings.max_context_images:
            seen_pages.add(page_key)
            image_paths.append(
                settings.storage_dir / meta["doc_id"] / "pages" / f"page_{meta['page_number']}.png"
            )

    answer = llm.answer_query(payload.question, text_context, image_paths)
    return QueryResponse(answer=answer, citations=citations)
