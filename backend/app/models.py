from typing import Optional

from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    num_pages: Optional[int] = None
    error: Optional[str] = None
    created_at: str


class QueryRequest(BaseModel):
    question: str
    doc_ids: Optional[list[str]] = None
    top_k: int = 5


class Citation(BaseModel):
    doc_id: str
    doc_name: str
    page_number: int
    snippet: str
    image_url: str


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
