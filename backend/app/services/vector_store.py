import json
import threading

import faiss
import numpy as np

from app.config import settings

_INDEX_PATH = settings.vector_store_dir / "index.faiss"
_META_PATH = settings.vector_store_dir / "metadata.json"

_lock = threading.Lock()
_index: faiss.Index | None = None
_metadata: dict[str, dict] = {}
_next_id = 0


def _load() -> None:
    global _index, _metadata, _next_id
    if _INDEX_PATH.exists() and _META_PATH.exists():
        _index = faiss.read_index(str(_INDEX_PATH))
        with open(_META_PATH, "r", encoding="utf-8") as f:
            _metadata = json.load(f)
        _next_id = max((int(key) for key in _metadata), default=-1) + 1
    else:
        _index = None
        _metadata = {}
        _next_id = 0


def _ensure_index(dim: int) -> faiss.Index:
    global _index
    if _index is None:
        _index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
    return _index


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


def _persist() -> None:
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    if _index is not None:
        faiss.write_index(_index, str(_INDEX_PATH))
    with open(_META_PATH, "w", encoding="utf-8") as f:
        json.dump(_metadata, f)


_load()


def add_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    global _next_id
    with _lock:
        vectors = _normalize(np.array(embeddings, dtype="float32"))
        index = _ensure_index(vectors.shape[1])

        int_ids = []
        for chunk_id, text, meta in zip(ids, documents, metadatas):
            int_id = _next_id
            _next_id += 1
            int_ids.append(int_id)
            _metadata[str(int_id)] = {**meta, "chunk_id": chunk_id, "text": text}

        index.add_with_ids(vectors, np.array(int_ids, dtype="int64"))
        _persist()


def query(embedding: list[float], n_results: int = 5, doc_ids: list[str] | None = None) -> dict:
    with _lock:
        if _index is None or _index.ntotal == 0:
            return {"documents": [[]], "metadatas": [[]]}

        vector = _normalize(np.array([embedding], dtype="float32"))
        # over-fetch so post-hoc doc_id filtering still leaves n_results candidates
        k = min(_index.ntotal, max(n_results * 5, n_results) if doc_ids else n_results)
        _, indices = _index.search(vector, k)

        documents: list[str] = []
        metadatas: list[dict] = []
        for idx in indices[0]:
            if idx == -1:
                continue
            meta = _metadata.get(str(int(idx)))
            if meta is None:
                continue
            if doc_ids and meta["doc_id"] not in doc_ids:
                continue
            metadatas.append(
                {"doc_id": meta["doc_id"], "doc_name": meta["doc_name"], "page_number": meta["page_number"]}
            )
            documents.append(meta["text"])
            if len(documents) >= n_results:
                break

        return {"documents": [documents], "metadatas": [metadatas]}


def delete_document(doc_id: str) -> None:
    with _lock:
        ids_to_remove = [int(key) for key, meta in _metadata.items() if meta["doc_id"] == doc_id]
        if ids_to_remove and _index is not None:
            _index.remove_ids(np.array(ids_to_remove, dtype="int64"))
        for key in [k for k, meta in _metadata.items() if meta["doc_id"] == doc_id]:
            del _metadata[key]
        _persist()
