"""Local cross-encoder reranker."""
from __future__ import annotations

import math
import os
import threading
import time
from pathlib import Path
from typing import List, Optional, Sequence

from langchain_core.documents import Document

from app.config import LOCAL_MODELS_OFFLINE, PIPELINE_CONFIG
from app.services.pipeline_timing import current_timing
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.reranking.cross_encoder")

DEFAULT_RERANKER_MODEL = "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected"
_REQUIRED_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
)


class CrossEncoderReranker:
    """Local cross-encoder reranker loaded from a filesystem artifact."""

    def __init__(
        self,
        model: str = DEFAULT_RERANKER_MODEL,
        device: str | None = None,
        batch_size: int | None = None,
        max_length: int | None = None,
        fail_open: bool | None = None,
        local_files_only: bool = LOCAL_MODELS_OFFLINE,
    ):
        self._model_path = model
        self._device = device if device is not None else PIPELINE_CONFIG.get("reranker_device", "cpu")
        self._batch_size = batch_size if batch_size is not None else PIPELINE_CONFIG.get("reranker_batch_size", 8)
        self._max_length = max_length if max_length is not None else PIPELINE_CONFIG.get("reranker_max_length", 512)
        self._fail_open = (
            PIPELINE_CONFIG.get("reranker_fail_open", False)
            if fail_open is None
            else fail_open
        )
        self._local_files_only = local_files_only
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._lock = threading.Lock()

        if self._batch_size <= 0:
            raise ValueError(f"RERANKER_BATCH_SIZE must be greater than 0; got {self._batch_size}.")
        if self._max_length <= 0:
            raise ValueError(f"RERANKER_MAX_LENGTH must be greater than 0; got {self._max_length}.")
        self._validate_local_artifact()

        if LOCAL_MODELS_OFFLINE:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        logger.info(
            "Local CrossEncoderReranker configured: model=%s device=%s batch_size=%d max_length=%d fail_open=%s",
            self._model_path,
            self._device,
            self._batch_size,
            self._max_length,
            self._fail_open,
        )

    @property
    def strategy_name(self) -> str:
        return f"cross_encoder({self._model_path})"

    def _validate_local_artifact(self) -> None:
        if not self._model_path:
            raise ValueError("RERANKER_MODEL must be a local path when PIPELINE_RERANKING=cross_encoder.")

        path = Path(self._model_path)
        if not path.exists() or not path.is_dir():
            raise FileNotFoundError(
                f"Local reranker model directory does not exist: {path}. "
                "Set RERANKER_MODEL to one validated candidate directory."
            )

        missing = [name for name in _REQUIRED_FILES if not (path / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Local reranker artifact at {path} is missing required files: {', '.join(missing)}."
            )

    def _load(self):
        if self._model is None or self._tokenizer is None:
            with self._lock:
                if self._model is None or self._tokenizer is None:
                    try:
                        import torch
                        from transformers import AutoModelForSequenceClassification, AutoTokenizer
                    except ImportError as exc:  # pragma: no cover - dependency check
                        raise RuntimeError(
                            "torch and transformers are required for local reranker inference."
                        ) from exc

                    logger.info("Loading local reranker from %s", self._model_path)
                    load_start = time.perf_counter_ns()
                    tokenizer = AutoTokenizer.from_pretrained(
                        self._model_path,
                        local_files_only=self._local_files_only,
                    )
                    model = AutoModelForSequenceClassification.from_pretrained(
                        self._model_path,
                        local_files_only=self._local_files_only,
                    )
                    model.to(self._device)
                    model.eval()
                    self._torch = torch
                    self._tokenizer = tokenizer
                    self._model = model
                    collector = current_timing()
                    if collector is not None:
                        collector.mark_reranker_model_load((time.perf_counter_ns() - load_start) / 1_000_000)
        return self._tokenizer, self._model, self._torch

    def _score_batch(self, query: str, texts: Sequence[str]) -> List[float]:
        tokenizer, model, torch = self._load()
        collector = current_timing()
        if collector is not None:
            with collector.stage("reranking"):
                encoded = tokenizer(
                    list(zip([query] * len(texts), texts)),
                    padding=True,
                    truncation=True,
                    max_length=self._max_length,
                    return_tensors="pt",
                )
                encoded = {key: value.to(self._device) for key, value in encoded.items()}

                with torch.inference_mode():
                    outputs = model(**encoded)
                    logits = outputs.logits
        else:
            encoded = tokenizer(
                list(zip([query] * len(texts), texts)),
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            encoded = {key: value.to(self._device) for key, value in encoded.items()}

            with torch.inference_mode():
                outputs = model(**encoded)
                logits = outputs.logits

        if logits.ndim == 1:
            logits = logits.unsqueeze(-1)
        if logits.shape[0] != len(texts):
            raise RuntimeError(
                f"Reranker output batch mismatch: expected {len(texts)}, got {logits.shape[0]}."
            )
        if logits.shape[-1] < 1:
            raise RuntimeError(f"Reranker logits have invalid shape: {tuple(logits.shape)}.")

        scores = logits[:, 0].detach().cpu().float().tolist()
        if not all(math.isfinite(float(score)) for score in scores):
            raise RuntimeError("Reranker output contains NaN or Inf.")
        return [float(score) for score in scores]

    def _score(self, query: str, documents: List[Document]) -> List[float]:
        scores: List[float] = []
        for start in range(0, len(documents), self._batch_size):
            batch = documents[start:start + self._batch_size]
            scores.extend(self._score_batch(query, [doc.page_content for doc in batch]))
        return scores

    @staticmethod
    def _fail_open_result(documents: List[Document], top_k: int) -> List[Document]:
        return documents[:max(0, top_k)]

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        if not documents:
            return []
        if top_k <= 0:
            return []

        try:
            scores = self._score(query, documents)
        except Exception as exc:
            if self._fail_open:
                logger.warning("Local cross-encoder failed open; preserving original order: %s", exc)
                return self._fail_open_result(documents, top_k)
            raise RuntimeError(f"Local cross-encoder reranking failed for {self._model_path}: {exc}") from exc

        collector = current_timing()
        if collector is not None:
            with collector.stage("reranking"):
                scored_docs = []
                for index, (score, doc) in enumerate(zip(scores, documents)):
                    metadata = dict(doc.metadata or {})
                    metadata["rerank_score"] = score
                    scored_docs.append(
                        (
                            score,
                            index,
                            Document(page_content=doc.page_content, metadata=metadata),
                        )
                    )
                scored_docs.sort(key=lambda item: (-item[0], item[1]))
        else:
            scored_docs = []
            for index, (score, doc) in enumerate(zip(scores, documents)):
                metadata = dict(doc.metadata or {})
                metadata["rerank_score"] = score
                scored_docs.append(
                    (
                        score,
                        index,
                        Document(page_content=doc.page_content, metadata=metadata),
                    )
                )
            scored_docs.sort(key=lambda item: (-item[0], item[1]))
        results = [doc for _, _, doc in scored_docs[:top_k]]
        logger.info(
            "Local CrossEncoder reranked %d -> %d documents (top score: %.4f)",
            len(documents),
            len(results),
            scored_docs[0][0] if scored_docs else 0.0,
        )
        return results
