from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_vision_model: str = "llava"
    ollama_embed_model: str = "nomic-embed-text"

    storage_dir: Path = BASE_DIR / "data" / "storage"
    vector_store_dir: Path = BASE_DIR / "data" / "vector_store"

    allowed_origins: str = "http://localhost:5173"

    max_context_chunks: int = 5
    max_context_images: int = 3

    chunk_size: int = 800
    chunk_overlap: int = 150

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
