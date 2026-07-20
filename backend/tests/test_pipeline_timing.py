import json
import sys
import types

import pytest

from app.services.pipeline_timing import (
    PipelineTimingCollector,
    current_timing,
    reset_current_timing,
    set_current_timing,
)


def test_timing_collector_records_stage_and_missing_stage_is_safe():
    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)

    with collector.stage("query_embedding"):
        pass

    payload = collector.payload("success")
    assert payload["event"] == "pipeline_timing"
    assert payload["request_id"] == "req-1"
    assert payload["durations_ms"]["query_embedding"] >= 0
    assert payload["durations_ms"]["total"] >= 0
    assert "reranking" not in payload["durations_ms"]


def test_disabled_collector_does_not_emit(monkeypatch):
    emitted = []
    monkeypatch.setattr("app.services.pipeline_timing.logger.info", lambda msg: emitted.append(msg))
    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=False)

    collector.emit_once("success")

    assert emitted == []


def test_emit_once_logs_single_sanitized_payload(monkeypatch):
    emitted = []
    monkeypatch.setattr("app.services.pipeline_timing.logger.info", lambda msg: emitted.append(json.loads(msg)))
    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)

    collector.emit_once("error")
    collector.emit_once("success")

    assert len(emitted) == 1
    payload = emitted[0]
    assert payload["outcome"] == "error"
    assert "query" not in json.dumps(payload).lower()
    assert "page_content" not in json.dumps(payload).lower()
    assert "answer" not in json.dumps(payload).lower()
    assert "api_key" not in json.dumps(payload).lower()


def test_model_load_flags_are_separate_from_compute():
    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)
    collector.mark_embedding_model_load(10)
    collector.mark_reranker_model_load(20)
    collector.add_duration("query_embedding", 3)
    collector.add_duration("reranking", 4)

    payload = collector.payload("success")

    assert payload["request_was_cold"] is True
    assert payload["embedding_was_cold"] is True
    assert payload["reranker_was_cold"] is True
    assert payload["durations_ms"]["model_load"] == 30
    assert payload["durations_ms"]["query_embedding"] == 3
    assert payload["durations_ms"]["reranking"] == 4


def test_streaming_first_token_and_completion_metrics():
    collector = PipelineTimingCollector("req-1", "/chat/stream", streaming=True, enabled=True)
    collector.add_duration("llm_time_to_first_token", 12)
    collector.mark_first_token()
    collector.add_duration("llm_generation", 40)

    payload = collector.payload("cancelled")

    assert payload["outcome"] == "cancelled"
    assert payload["durations_ms"]["llm_stream_after_first_token"] == 28
    assert payload["durations_ms"]["total_time_to_first_token"] >= 0


def test_contextvar_collectors_do_not_overwrite_each_other():
    first = PipelineTimingCollector("first", "/chat", streaming=False, enabled=True)
    second = PipelineTimingCollector("second", "/chat", streaming=False, enabled=True)

    token = set_current_timing(first)
    assert current_timing() is first
    inner_token = set_current_timing(second)
    assert current_timing() is second
    reset_current_timing(inner_token)
    assert current_timing() is first
    reset_current_timing(token)
    assert current_timing() is None


def _make_embedding_dir(tmp_path):
    model_dir = tmp_path / "embedding"
    model_dir.mkdir()
    for name in (
        "config.json",
        "modules.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "model.safetensors",
    ):
        (model_dir / name).write_text("{}", encoding="utf-8")
    return model_dir


def test_local_embedding_records_cold_load_and_compute(monkeypatch, tmp_path):
    from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding

    model_dir = _make_embedding_dir(tmp_path)

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def eval(self):
            pass

        def encode(self, texts, **kwargs):
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeSentenceTransformer)
    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)
    token = set_current_timing(collector)
    try:
        embedding = HuggingFaceEndpointEmbedding(
            model=str(model_dir),
            mode="local",
            expected_dimension=2,
        )
        assert embedding.embed_query("q") == [1.0, 0.0]
        assert embedding.embed_query("q2") == [1.0, 0.0]
    finally:
        reset_current_timing(token)

    payload = collector.payload("success")
    assert payload["embedding_was_cold"] is True
    assert payload["durations_ms"]["embedding_model_load"] >= 0
    assert payload["durations_ms"]["query_embedding"] >= 0
    assert payload["durations_ms"]["model_load"] == payload["durations_ms"]["embedding_model_load"]


def test_reranker_records_cold_load(monkeypatch, tmp_path):
    from app.services.reranking.cross_encoder import CrossEncoderReranker

    model_dir = tmp_path / "reranker"
    model_dir.mkdir()
    for name in (
        "config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "sentencepiece.bpe.model",
    ):
        (model_dir / name).write_text("{}", encoding="utf-8")

    class FakeTokenizer:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

    class FakeModel:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def to(self, device):
            return self

        def eval(self):
            return None

    fake_transformers = types.SimpleNamespace(
        AutoTokenizer=FakeTokenizer,
        AutoModelForSequenceClassification=FakeModel,
    )
    fake_torch = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "transformers", fake_transformers)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)
    token = set_current_timing(collector)
    try:
        reranker = CrossEncoderReranker(model=str(model_dir))
        reranker._load()
        reranker._load()
    finally:
        reset_current_timing(token)

    payload = collector.payload("success")
    assert payload["reranker_was_cold"] is True
    assert payload["durations_ms"]["reranker_model_load"] >= 0


def test_rag_pipeline_records_context_building():
    from langchain_core.documents import Document
    from app.services.pipeline import RAGPipeline

    class Rewriter:
        def rewrite(self, query):
            return "legal", [query]

    class Searcher:
        strategy_name = "fake"

        def search(self, queries, k, category=None):
            return [Document(page_content="text", metadata={"id": "1"})]

    class Reranker:
        strategy_name = "fake"

        def rerank(self, query, documents, top_k):
            return documents[:top_k]

    class ContextBuilder:
        strategy_name = "fake"

        def build(self, docs):
            return "\n".join(doc.page_content for doc in docs)

    collector = PipelineTimingCollector("req-1", "/chat", streaming=False, enabled=True)
    token = set_current_timing(collector)
    try:
        pipeline = RAGPipeline(Rewriter(), Searcher(), Reranker(), ContextBuilder())
        docs, context = pipeline.retrieve("q")
    finally:
        reset_current_timing(token)

    assert len(docs) == 1
    assert context == "text"
    assert collector.payload("success")["durations_ms"]["context_building"] >= 0
