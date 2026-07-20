import app.services.pipeline as pipeline_module
import app.config as config_module


def test_get_pipeline_initializes_when_missing(monkeypatch):
    pipeline_module._pipeline = None

    def fake_init_pipeline():
        pipeline_module._pipeline = object()

    monkeypatch.setattr(pipeline_module, "init_pipeline", fake_init_pipeline)

    assert pipeline_module.get_pipeline() is pipeline_module._pipeline


def test_remote_first_embedding_does_not_initialize_ollama(monkeypatch):
    pipeline_module._embedding_cache = {}

    class FakeHuggingFaceEmbedding:
        def __init__(self, api_key=None):
            self.api_key = api_key

    class FakeOllamaEmbedding:
        def __init__(self):
            raise AssertionError("remote_first must not initialize local Ollama embeddings")

    monkeypatch.setattr(config_module, "INFERENCE_STRATEGY", "remote_first")
    monkeypatch.setattr(pipeline_module, "HuggingFaceEndpointEmbedding", FakeHuggingFaceEmbedding)
    monkeypatch.setattr(pipeline_module, "OllamaEmbedding", FakeOllamaEmbedding)

    embedding = pipeline_module._get_embedding("runtime-hf-token")

    assert isinstance(embedding, FakeHuggingFaceEmbedding)
    assert embedding.api_key == "runtime-hf-token"


def test_cross_encoder_wires_local_reranker_from_config(monkeypatch):
    class FakeCrossEncoderReranker:
        def __init__(self, model, device, batch_size, max_length, fail_open):
            self.model = model
            self.device = device
            self.batch_size = batch_size
            self.max_length = max_length
            self.fail_open = fail_open

    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranking", "cross_encoder")
    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranker_model", "/models/reranker-candidate")
    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranker_device", "cpu")
    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranker_batch_size", 4)
    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranker_max_length", 256)
    monkeypatch.setitem(pipeline_module.PIPELINE_CONFIG, "reranker_fail_open", True)
    monkeypatch.setattr(pipeline_module, "CrossEncoderReranker", FakeCrossEncoderReranker)

    reranker = pipeline_module._create_reranker()

    assert isinstance(reranker, FakeCrossEncoderReranker)
    assert reranker.model == "/models/reranker-candidate"
    assert reranker.batch_size == 4
    assert reranker.max_length == 256
    assert reranker.fail_open is True


def test_preload_local_models_loads_singletons_without_warmup(monkeypatch):
    calls = []

    class FakeEmbedding:
        def _get_local_engine(self):
            calls.append("embedding_load")

        def embed_query(self, query):
            calls.append("embedding_warmup")
            return [0.0]

    class FakeReranker:
        def _load(self):
            calls.append("reranker_load")

        def rerank(self, query, documents, top_k):
            calls.append("reranker_warmup")
            return documents[:top_k]

    class FakePipeline:
        reranker = FakeReranker()

    monkeypatch.setattr(pipeline_module, "get_pipeline", lambda: FakePipeline())
    monkeypatch.setattr(pipeline_module, "_get_embedding", lambda: FakeEmbedding())

    timings = pipeline_module.preload_local_models(warmup=False)

    assert calls == ["embedding_load", "reranker_load"]
    assert "total_startup_model_ms" in timings


def test_preload_local_models_warmup_uses_synthetic_inputs(monkeypatch):
    calls = []

    class FakeEmbedding:
        def _get_local_engine(self):
            calls.append(("embedding_load", None))

        def embed_query(self, query):
            calls.append(("embedding_warmup", query))
            return [0.0]

    class FakeReranker:
        def _load(self):
            calls.append(("reranker_load", None))

        def rerank(self, query, documents, top_k):
            calls.append(("reranker_warmup", query, documents[0].page_content, top_k))
            return documents[:top_k]

    class FakePipeline:
        reranker = FakeReranker()

    monkeypatch.setattr(pipeline_module, "get_pipeline", lambda: FakePipeline())
    monkeypatch.setattr(pipeline_module, "_get_embedding", lambda: FakeEmbedding())

    pipeline_module.preload_local_models(warmup=True)

    assert ("embedding_warmup", "kiểm tra hệ thống") in calls
    assert ("reranker_warmup", "kiểm tra hệ thống", "nội dung kiểm tra", 1) in calls
