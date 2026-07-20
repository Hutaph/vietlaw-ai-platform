import pytest

from app.services import semantic_cache
from app.services.storage import (
    StorageInitializationError,
    _ensure_collection_dimension,
)


class _Vector:
    def __init__(self, size):
        self.size = size


class _Params:
    def __init__(self, vectors):
        self.vectors = vectors


class _Config:
    def __init__(self, vectors):
        self.params = _Params(vectors)


class _CollectionInfo:
    def __init__(self, vectors):
        self.config = _Config(vectors)


def test_named_collection_dimension_match():
    info = _CollectionInfo({"text-dense": _Vector(1024)})

    _ensure_collection_dimension(info, "vietlaw_clauses", "text-dense", 1024)


def test_named_collection_dimension_mismatch_raises():
    info = _CollectionInfo({"text-dense": _Vector(768)})

    with pytest.raises(StorageInitializationError, match="Re-index"):
        _ensure_collection_dimension(info, "vietlaw_clauses", "text-dense", 1024)


def test_semantic_cache_rejects_wrong_dimension(monkeypatch):
    monkeypatch.setattr(semantic_cache, "ENABLE_SEMANTIC_CACHE", True)
    monkeypatch.setattr(semantic_cache, "EMBEDDING_DIMENSION", 3)

    with pytest.raises(ValueError, match="dimension mismatch"):
        semantic_cache.check_cache([0.0, 1.0])


def test_semantic_cache_uses_configured_collection(monkeypatch):
    class FakeClient:
        def __init__(self):
            self.collection_name = None

        def upsert(self, collection_name, points):
            self.collection_name = collection_name

    fake_client = FakeClient()
    monkeypatch.setattr(semantic_cache, "ENABLE_SEMANTIC_CACHE", True)
    monkeypatch.setattr(semantic_cache, "EMBEDDING_DIMENSION", 2)
    monkeypatch.setattr(semantic_cache, "SEMANTIC_CACHE_COLLECTION", "semantic_cache_bge_m3_ft_v1")
    monkeypatch.setattr(semantic_cache, "_qdrant_client", fake_client)

    semantic_cache.update_cache([0.0, 1.0], "query", "answer", [], [])

    assert fake_client.collection_name == "semantic_cache_bge_m3_ft_v1"
