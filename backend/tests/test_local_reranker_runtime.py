import sys
import types

import pytest
from langchain_core.documents import Document

from app.services.reranking.cross_encoder import CrossEncoderReranker


def _make_reranker_dir(tmp_path):
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
    return model_dir


def test_reranker_stable_descending_sort_and_metadata(tmp_path):
    model_dir = _make_reranker_dir(tmp_path)

    class FakeReranker(CrossEncoderReranker):
        def _score(self, query, documents):
            return [0.2, 0.9, 0.9]

    docs = [
        Document(page_content="a", metadata={"id": "a"}),
        Document(page_content="b", metadata={"id": "b"}),
        Document(page_content="c", metadata={"id": "c"}),
    ]
    reranker = FakeReranker(model=str(model_dir), batch_size=2, max_length=16)

    result = reranker.rerank("q", docs, top_k=3)

    assert [doc.metadata["id"] for doc in result] == ["b", "c", "a"]
    assert result[0].metadata["rerank_score"] == 0.9
    assert "rerank_score" not in docs[0].metadata


def test_reranker_top_k_and_empty_input(tmp_path):
    model_dir = _make_reranker_dir(tmp_path)

    class FakeReranker(CrossEncoderReranker):
        def _score(self, query, documents):
            return [float(index) for index, _ in enumerate(documents)]

    reranker = FakeReranker(model=str(model_dir), batch_size=2, max_length=16)
    docs = [Document(page_content=str(index), metadata={"id": index}) for index in range(4)]

    assert reranker.rerank("q", [], top_k=2) == []
    assert reranker.rerank("q", docs, top_k=0) == []
    assert [doc.metadata["id"] for doc in reranker.rerank("q", docs, top_k=2)] == [3, 2]


def test_reranker_fail_open_false_raises(tmp_path):
    model_dir = _make_reranker_dir(tmp_path)

    class FakeReranker(CrossEncoderReranker):
        def _score(self, query, documents):
            raise RuntimeError("boom")

    reranker = FakeReranker(model=str(model_dir), fail_open=False)

    with pytest.raises(RuntimeError, match="Local cross-encoder reranking failed"):
        reranker.rerank("q", [Document(page_content="a")], top_k=1)


def test_reranker_fail_open_true_preserves_order(tmp_path):
    model_dir = _make_reranker_dir(tmp_path)

    class FakeReranker(CrossEncoderReranker):
        def _score(self, query, documents):
            raise RuntimeError("boom")

    reranker = FakeReranker(model=str(model_dir), fail_open=True)
    docs = [Document(page_content="a"), Document(page_content="b")]

    assert reranker.rerank("q", docs, top_k=1) == [docs[0]]


def test_reranker_lazy_loads_model_once_and_batches(monkeypatch, tmp_path):
    torch = pytest.importorskip("torch")
    model_dir = _make_reranker_dir(tmp_path)
    calls = {"tokenizer": 0, "model": 0, "batches": []}

    class FakeBatch(dict):
        def to(self, device):
            return self

    class FakeTokenizer:
        def __call__(self, pairs, padding, truncation, max_length, return_tensors):
            calls["batches"].append((len(pairs), max_length))
            return {"input_ids": FakeBatch({"values": torch.ones(len(pairs), 2, dtype=torch.long)})["values"]}

    class FakeModel:
        def to(self, device):
            self.device = device
            return self

        def eval(self):
            self.eval_called = True

        def __call__(self, **encoded):
            batch_size = encoded["input_ids"].shape[0]
            logits = torch.arange(batch_size, dtype=torch.float32).reshape(batch_size, 1)
            return types.SimpleNamespace(logits=logits)

    class FakeAutoTokenizer:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            calls["tokenizer"] += 1
            assert local_files_only is True
            return FakeTokenizer()

    class FakeAutoModel:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            calls["model"] += 1
            assert local_files_only is True
            return FakeModel()

    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            AutoTokenizer=FakeAutoTokenizer,
            AutoModelForSequenceClassification=FakeAutoModel,
        ),
    )

    reranker = CrossEncoderReranker(
        model=str(model_dir),
        device="cpu",
        batch_size=2,
        max_length=32,
        local_files_only=True,
    )
    docs = [Document(page_content=str(index), metadata={"id": index}) for index in range(3)]

    reranker.rerank("q", docs, top_k=3)
    reranker.rerank("q", docs[:1], top_k=1)

    assert calls["tokenizer"] == 1
    assert calls["model"] == 1
    assert calls["batches"] == [(2, 32), (1, 32), (1, 32)]


def test_reranker_source_does_not_reference_inference_client():
    import inspect
    import app.services.reranking.cross_encoder as module

    assert "InferenceClient" not in inspect.getsource(module)
