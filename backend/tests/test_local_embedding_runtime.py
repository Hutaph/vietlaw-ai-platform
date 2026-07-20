import math

import pytest

from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding


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


def test_local_embedding_lazy_loads_once_and_batches(monkeypatch, tmp_path):
    model_dir = _make_embedding_dir(tmp_path)
    calls = {"init": 0, "encode": []}

    class FakeSentenceTransformer:
        def __init__(self, model_name, device, local_files_only):
            calls["init"] += 1
            self.model_name = model_name
            self.device = device
            self.local_files_only = local_files_only

        def eval(self):
            calls["eval"] = True

        def encode(self, texts, batch_size, normalize_embeddings, convert_to_numpy, show_progress_bar):
            calls["encode"].append(
                {
                    "texts": texts,
                    "batch_size": batch_size,
                    "normalize": normalize_embeddings,
                    "local": self.local_files_only,
                }
            )
            return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        FakeSentenceTransformer,
    )

    embedding = HuggingFaceEndpointEmbedding(
        model=str(model_dir),
        mode="local",
        device="cpu",
        batch_size=2,
        normalize_embeddings=True,
        expected_dimension=2,
        local_files_only=True,
    )

    assert embedding.embed_query("q") == [1.0, 0.0]
    assert embedding.embed_documents(["a", "b"]) == [[1.0, 0.0], [1.0, 0.0]]
    assert calls["init"] == 1
    assert calls["eval"] is True
    assert calls["encode"][0]["batch_size"] == 2
    assert calls["encode"][0]["normalize"] is True


def test_local_embedding_rejects_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        HuggingFaceEndpointEmbedding(
            model=str(tmp_path / "missing"),
            mode="local",
            expected_dimension=2,
        )


def test_local_embedding_rejects_dimension_mismatch(monkeypatch, tmp_path):
    model_dir = _make_embedding_dir(tmp_path)

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def eval(self):
            pass

        def encode(self, *args, **kwargs):
            return [[1.0]]

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeSentenceTransformer)

    embedding = HuggingFaceEndpointEmbedding(
        model=str(model_dir),
        mode="local",
        expected_dimension=2,
    )

    with pytest.raises(RuntimeError, match="dimension mismatch"):
        embedding.embed_query("q")


def test_local_embedding_rejects_non_finite(monkeypatch, tmp_path):
    model_dir = _make_embedding_dir(tmp_path)

    class FakeSentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass

        def eval(self):
            pass

        def encode(self, *args, **kwargs):
            return [[math.inf, 0.0]]

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeSentenceTransformer)

    embedding = HuggingFaceEndpointEmbedding(
        model=str(model_dir),
        mode="local",
        expected_dimension=2,
    )

    with pytest.raises(RuntimeError, match="NaN or Inf"):
        embedding.embed_query("q")
