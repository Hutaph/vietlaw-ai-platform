import asyncio

import pytest
from langchain_core.documents import Document

from app.services.search.qdrant_search import QdrantSearcher, contains_explicit_legal_citation


class _FallbackSearcher:
    def __init__(self):
        self.calls = 0

    def search(self, query, k=20, category=None):
        self.calls += 1
        return [Document(page_content="fallback", metadata={"id": "fallback"})]


class _AsyncFallbackSearcher(_FallbackSearcher):
    async def asearch(self, query, k=20, category=None):
        self.calls += 1
        return [Document(page_content="async fallback", metadata={"id": "fallback"})]


def test_qdrant_error_reraises_when_fallback_disabled(monkeypatch):
    searcher = QdrantSearcher(vectorstore=None, fallback_searcher=None, collection_name="vietlaw_clauses")
    monkeypatch.setattr(searcher, "_search_qdrant", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("missing collection")))

    with pytest.raises(RuntimeError, match="FAISS fallback is disabled") as exc_info:
        searcher.search("query")

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_qdrant_error_uses_fallback_only_when_enabled(monkeypatch):
    fallback = _FallbackSearcher()
    searcher = QdrantSearcher(vectorstore=None, fallback_searcher=fallback, collection_name="vietlaw_clauses")
    monkeypatch.setattr(searcher, "_search_qdrant", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("qdrant down")))

    docs = searcher.search("query")

    assert fallback.calls == 1
    assert [doc.metadata["id"] for doc in docs] == ["fallback"]


def test_qdrant_success_does_not_call_fallback(monkeypatch):
    fallback = _FallbackSearcher()
    searcher = QdrantSearcher(vectorstore=None, fallback_searcher=fallback, collection_name="vietlaw_clauses")
    expected = [Document(page_content="qdrant", metadata={"id": "qdrant"})]
    monkeypatch.setattr(searcher, "_search_qdrant", lambda *args, **kwargs: expected)

    docs = searcher.search("query")

    assert fallback.calls == 0
    assert docs == expected


def test_async_qdrant_error_reraises_when_fallback_disabled(monkeypatch):
    async def immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    searcher = QdrantSearcher(vectorstore=None, fallback_searcher=None, collection_name="vietlaw_clauses")
    monkeypatch.setattr(asyncio, "to_thread", immediate_to_thread)
    monkeypatch.setattr(searcher, "_search_qdrant", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("auth failed")))

    with pytest.raises(RuntimeError, match="FAISS fallback is disabled"):
        asyncio.run(searcher.asearch("query"))


def test_async_qdrant_error_uses_fallback_only_when_enabled(monkeypatch):
    async def immediate_to_thread(func, /, *args, **kwargs):
        return func(*args, **kwargs)

    fallback = _AsyncFallbackSearcher()
    searcher = QdrantSearcher(vectorstore=None, fallback_searcher=fallback, collection_name="vietlaw_clauses")
    monkeypatch.setattr(asyncio, "to_thread", immediate_to_thread)
    monkeypatch.setattr(searcher, "_search_qdrant", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("qdrant down")))

    docs = asyncio.run(searcher.asearch("query"))

    assert fallback.calls == 1
    assert [doc.metadata["id"] for doc in docs] == ["fallback"]


def test_qdrant_factory_does_not_create_faiss_fallback_by_default(monkeypatch):
    from app.services import pipeline

    captured = {}

    class FakeQdrantSearcher:
        def __init__(self, vectorstore, fallback_searcher=None):
            captured["fallback_searcher"] = fallback_searcher

    monkeypatch.setattr(pipeline, "STORAGE_BACKEND", "qdrant_postgres")
    monkeypatch.setattr(pipeline, "ENABLE_FAISS_FALLBACK", False)
    monkeypatch.setattr(pipeline, "QdrantSearcher", FakeQdrantSearcher)

    pipeline._create_searcher(None)

    assert captured["fallback_searcher"] is None


def test_qdrant_factory_creates_faiss_fallback_when_enabled(monkeypatch):
    from app.services import pipeline

    captured = {}

    class FakeFAISSSearcher:
        def __init__(self, vectorstore):
            self.vectorstore = vectorstore

    class FakeQdrantSearcher:
        def __init__(self, vectorstore, fallback_searcher=None):
            captured["fallback_searcher"] = fallback_searcher

    monkeypatch.setattr(pipeline, "STORAGE_BACKEND", "qdrant")
    monkeypatch.setattr(pipeline, "ENABLE_FAISS_FALLBACK", True)
    monkeypatch.setattr(pipeline, "FAISSSearcher", FakeFAISSSearcher)
    monkeypatch.setattr(pipeline, "QdrantSearcher", FakeQdrantSearcher)

    pipeline._create_searcher(None)

    assert isinstance(captured["fallback_searcher"], FakeFAISSSearcher)


def test_qdrant_prefetch_widens_only_for_explicit_legal_citations():
    assert QdrantSearcher._prefetch_limit_for_queries(["query"], 10) == 20
    assert (
        QdrantSearcher._prefetch_limit_for_queries(["Theo Điều 45 khoản 1 Luật Đất đai 2024"], 10)
        == 40
    )
    assert QdrantSearcher._prefetch_limit_for_queries(["Đ45 K1"], 10) == 40
    assert (
        QdrantSearcher._prefetch_limit_for_queries(["Điều kiện chuyển nhượng quyền sử dụng đất là gì?"], 10)
        == 20
    )


@pytest.mark.parametrize(
    "query",
    [
        "Điều 45",
        "Điều 45 khoản 1",
        "Khoản 1 Điều 45",
        "điều 45, khoản 1",
        "Điều 45 Khoản 1 Luật Đất đai 2024",
        "Điểm a Khoản 1 Điều 45",
        "khoản 3 điều 27",
        "Đ45 K1",
        "Đ.45 K.1",
        "Điều 123",
        "Khoản 12 Điều 345",
    ],
)
def test_explicit_legal_citation_detector_positive_cases(query):
    assert contains_explicit_legal_citation(query)


@pytest.mark.parametrize(
    "query",
    [
        "Tôi có 45 ngày để nộp hồ sơ không?",
        "Khoản tiền 45 triệu đồng",
        "Diện tích đất là 45.1 mét vuông",
        "Hồ sơ số 45/2024",
        "Mức phạt từ 40 đến 45 triệu",
        "Tôi có 1 khoản vay",
        "Điểm thi của tôi là 8",
        "Năm 2024 tôi mua đất",
        "Chuyển nhượng đất cần điều kiện gì?",
    ],
)
def test_explicit_legal_citation_detector_negative_cases(query):
    assert not contains_explicit_legal_citation(query)


def test_faiss_storage_backend_still_requires_vectorstore(monkeypatch):
    from app.services import pipeline

    monkeypatch.setattr(pipeline, "STORAGE_BACKEND", "faiss")
    monkeypatch.setattr(pipeline, "_faiss_vectorstore", None)

    with pytest.raises(RuntimeError, match="FAISS vectorstore"):
        pipeline._create_searcher(None)
