import pytest

from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.reranking.cross_encoder import CrossEncoderReranker


def _make_model_dir(tmp_path, files):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    for name in files:
        (model_dir / name).write_text("{}", encoding="utf-8")
    return model_dir


def test_embedding_rejects_invalid_batch_size(tmp_path):
    model_dir = _make_model_dir(
        tmp_path,
        [
            "config.json",
            "modules.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "model.safetensors",
        ],
    )

    with pytest.raises(ValueError, match="EMBEDDING_BATCH_SIZE"):
        HuggingFaceEndpointEmbedding(model=str(model_dir), mode="local", batch_size=0)


def test_reranker_rejects_invalid_max_length(tmp_path):
    model_dir = _make_model_dir(
        tmp_path,
        [
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "sentencepiece.bpe.model",
        ],
    )

    with pytest.raises(ValueError, match="RERANKER_MAX_LENGTH"):
        CrossEncoderReranker(model=str(model_dir), max_length=0)


def test_reranker_rejects_missing_local_path(tmp_path):
    with pytest.raises(FileNotFoundError, match="RERANKER_MODEL"):
        CrossEncoderReranker(model=str(tmp_path / "missing"))
