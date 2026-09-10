from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.config import settings


@dataclass
class ProcessedPage:
    page_number: int
    text: str
    image_path: Path


@dataclass
class PageChunk:
    page_number: int
    chunk_index: int
    text: str


def render_and_extract(pdf_path: Path, images_dir: Path, dpi: int = 150) -> list[ProcessedPage]:
    """Extract text per page and render each page to a PNG for visual/layout queries."""
    images_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    pages: list[ProcessedPage] = []
    doc = pymupdf.open(pdf_path)
    try:
        for index, page in enumerate(doc):
            page_number = index + 1
            text = page.get_text("text")
            pixmap = page.get_pixmap(matrix=matrix)
            image_path = images_dir / f"page_{page_number}.png"
            pixmap.save(str(image_path))
            pages.append(ProcessedPage(page_number=page_number, text=text, image_path=image_path))
    finally:
        doc.close()
    return pages


def chunk_text(text: str, page_number: int) -> list[PageChunk]:
    """Split a page's text into overlapping chunks. Chunks never span pages so each
    chunk can be cited back to exactly one page image."""
    text = text.strip()
    if not text:
        return []

    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    length = len(text)

    chunks: list[PageChunk] = []
    start = 0
    chunk_index = 0
    while start < length:
        end = min(start + chunk_size, length)
        piece = text[start:end].strip()
        if piece:
            chunks.append(PageChunk(page_number=page_number, chunk_index=chunk_index, text=piece))
            chunk_index += 1
        if end == length:
            break
        start = end - overlap
    return chunks
