import json
import threading
from pathlib import Path

from app.config import settings

_lock = threading.Lock()


def _meta_path() -> Path:
    return settings.storage_dir / "documents.json"


def _load() -> dict:
    path = _meta_path()
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    path = _meta_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_documents() -> list[dict]:
    with _lock:
        return list(_load().values())


def get_document(doc_id: str) -> dict | None:
    with _lock:
        return _load().get(doc_id)


def upsert_document(doc: dict) -> None:
    with _lock:
        data = _load()
        data[doc["id"]] = doc
        _save(data)


def delete_document(doc_id: str) -> None:
    with _lock:
        data = _load()
        data.pop(doc_id, None)
        _save(data)
