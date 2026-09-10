import ollama

from app.config import settings

_client = ollama.Client(host=settings.ollama_base_url)


def embed_text(text: str) -> list[float]:
    response = _client.embeddings(model=settings.ollama_embed_model, prompt=text)
    return response["embedding"]
