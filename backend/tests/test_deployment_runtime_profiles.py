import asyncio
from pathlib import Path

import pytest
from langchain_core.documents import Document

import app.config as config_module
from app.services.pipeline import RAGPipeline
from app.services.reranking.embedding_similarity import HuggingFaceEmbeddingSimilarityReranker


def test_serverless_profile_requires_remote_embedding(monkeypatch):
    monkeypatch.setattr(config_module, "RUNTIME_PROFILE", "serverless")
    monkeypatch.setattr(config_module, "HUGGINGFACE_EMBEDDING_MODE", "api")
    monkeypatch.setattr(config_module, "EMBEDDING_MODEL", "BAAI/bge-m3")

    config_module.validate_runtime_configuration()


def test_local_profile_rejects_hub_model_id(monkeypatch):
    monkeypatch.setattr(config_module, "RUNTIME_PROFILE", "local")
    monkeypatch.setattr(config_module, "HUGGINGFACE_EMBEDDING_MODE", "local")
    monkeypatch.setattr(config_module, "EMBEDDING_MODEL", "BAAI/bge-m3")

    try:
        config_module.validate_runtime_configuration()
    except ValueError as exc:
        assert "filesystem path" in str(exc)
    else:
        raise AssertionError("local profile accepted a Hub model id")


def test_async_retrieval_dispatches_search_once():
    calls = []

    class Rewriter:
        def rewrite(self, query):
            return "legal", [query]

    class Searcher:
        strategy_name = "fake"

        async def asearch(self, queries, k, category=None, api_key=None):
            calls.append((queries, api_key))
            return [Document(page_content="text", metadata={"id": "1"})]

    class Reranker:
        strategy_name = "none"

        def rerank(self, query, documents, top_k):
            return documents[:top_k]

    class ContextBuilder:
        strategy_name = "fake"

        def build(self, docs):
            return "\n".join(doc.page_content for doc in docs)

    pipeline = RAGPipeline(Rewriter(), Searcher(), Reranker(), ContextBuilder())
    docs, context = asyncio.run(
        pipeline.aretrieve(
            "q",
            domain="legal",
            queries=["q"],
            enable_reranker=False,
            embedding_api_key="request-token",
        )
    )

    assert len(calls) == 1
    assert calls[0][1] == "request-token"
    assert len(docs) == 1
    assert context == "text"


def test_remote_reranker_uses_request_credential(monkeypatch):
    created = []

    class FakeEmbedding:
        def __init__(self, model, api_key, mode):
            created.append((model, api_key, mode))

        def embed_query(self, text):
            return [1.0, 0.0]

        def embed_documents(self, texts):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(
        "app.services.reranking.embedding_similarity.HuggingFaceEndpointEmbedding",
        FakeEmbedding,
    )
    reranker = HuggingFaceEmbeddingSimilarityReranker(
        model="BAAI/bge-m3",
        api_key="server-token",
        max_candidates=10,
    )

    reranker.rerank(
        "q",
        [Document(page_content="doc", metadata={"id": "1"})],
        top_k=1,
        api_key="request-token",
    )

    assert created == [("BAAI/bge-m3", "request-token", "api")]


def test_production_requirements_exclude_local_model_runtime():
    backend_dir = Path(__file__).resolve().parents[1]
    production = (backend_dir / "requirements.txt").read_text(encoding="utf-8").lower()
    local = (backend_dir / "requirements-local.txt").read_text(encoding="utf-8").lower()

    for package in ("torch", "transformers", "sentence-transformers", "safetensors"):
        assert package not in production
        assert package in local


def test_chat_storage_mode_validation(monkeypatch):
    monkeypatch.setattr(config_module, "CHAT_STORAGE_MODE", "invalid")

    with pytest.raises(ValueError, match="CHAT_STORAGE_MODE"):
        config_module.validate_runtime_configuration()


@pytest.mark.parametrize("mode", ["browser", "postgres"])
def test_chat_storage_mode_is_independent_from_legal_storage(monkeypatch, mode):
    monkeypatch.setattr(config_module, "CHAT_STORAGE_MODE", mode)
    monkeypatch.setattr(config_module, "FRONTEND_CHAT_STORAGE_MODE", mode)
    monkeypatch.setattr(config_module, "RUNTIME_PROFILE", "serverless")
    monkeypatch.setattr(config_module, "HUGGINGFACE_EMBEDDING_MODE", "api")
    monkeypatch.setattr(config_module, "EMBEDDING_MODEL", "BAAI/bge-m3")
    monkeypatch.setattr(config_module, "STORAGE_BACKEND", "qdrant_postgres")

    config_module.validate_runtime_configuration()
    assert config_module.STORAGE_BACKEND == "qdrant_postgres"


def test_chat_storage_mode_rejects_frontend_mismatch(monkeypatch):
    monkeypatch.setattr(config_module, "CHAT_STORAGE_MODE", "browser")
    monkeypatch.setattr(config_module, "FRONTEND_CHAT_STORAGE_MODE", "postgres")

    with pytest.raises(ValueError, match="must match"):
        config_module.validate_runtime_configuration()


def test_browser_mode_disables_server_chat_persistence(monkeypatch):
    import app.services.storage as storage_module

    monkeypatch.setattr(storage_module, "CHAT_STORAGE_MODE", "browser")

    assert not storage_module.is_chat_persistence_enabled()
    assert storage_module.get_session_summary("session") is None
    assert storage_module.get_session_messages("session") == []
    assert storage_module.list_sessions() == []


def test_postgres_mode_keeps_server_chat_persistence(monkeypatch):
    import app.services.storage as storage_module

    monkeypatch.setattr(storage_module, "CHAT_STORAGE_MODE", "postgres")

    assert storage_module.is_chat_persistence_enabled()


def test_browser_mode_session_endpoints_do_not_expose_postgres(monkeypatch):
    import app.api.chat as chat_module

    monkeypatch.setattr(chat_module, "CHAT_STORAGE_MODE", "browser")

    assert asyncio.run(chat_module.get_sessions()) == {
        "storageMode": "browser",
        "sessions": [],
    }
    assert asyncio.run(chat_module.get_session_messages("session")) == {
        "storageMode": "browser",
        "messages": [],
    }
    assert asyncio.run(chat_module.delete_session("session")) == {
        "status": "skipped",
        "storageMode": "browser",
    }


def test_browser_mode_feedback_is_not_persisted(monkeypatch):
    import app.api.feedback as feedback_module

    monkeypatch.setattr(feedback_module, "CHAT_STORAGE_MODE", "browser")
    request = feedback_module.FeedbackRequest(
        message_id="message",
        session_id="session",
        feedback_type=1,
    )

    result = asyncio.run(feedback_module.submit_feedback(request))

    assert result["status"] == "skipped"
    assert result["storageMode"] == "browser"


def test_browser_mode_skips_memory_summary(monkeypatch):
    import app.services.memory_manager as memory_module

    monkeypatch.setattr(memory_module, "CHAT_STORAGE_MODE", "browser")
    monkeypatch.setattr(
        memory_module,
        "get_session_summary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("database read")),
    )

    asyncio.run(memory_module.summarize_session("session", "user", "assistant"))
