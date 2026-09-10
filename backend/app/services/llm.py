import base64
from pathlib import Path

import ollama

from app.config import settings

_client = ollama.Client(host=settings.ollama_base_url)

SYSTEM_PROMPT = (
    "You are a document intelligence assistant. You answer questions about PDF "
    "documents using the retrieved text excerpts and the page images provided. "
    "Page images may contain tables, charts, diagrams or layout information that "
    "is not captured in the text excerpts, so inspect them carefully when relevant. "
    "Always cite the page number(s) you used to answer, e.g. (p. 3). If the answer "
    "is not contained in the provided context, say so clearly instead of guessing."
)


def _encode_image(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def answer_query(question: str, text_context: list[dict], image_paths: list[Path]) -> str:
    context_block = "\n\n".join(
        f"[Document: {chunk['doc_name']}, Page {chunk['page_number']}]\n{chunk['text']}"
        for chunk in text_context
    )
    user_content = (
        f"Context excerpts:\n{context_block}\n\n"
        "Attached page images correspond to the most relevant pages above.\n\n"
        f"Question: {question}"
    )

    response = _client.chat(
        model=settings.ollama_vision_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_content,
                "images": [_encode_image(path) for path in image_paths],
            },
        ],
    )
    return response["message"]["content"]
