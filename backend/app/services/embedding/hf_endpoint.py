"""HuggingFace embedding adapter with API and local filesystem modes."""
from __future__ import annotations

import math
import os
import threading
import time
from pathlib import Path
from typing import List, Optional

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DEVICE,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    EMBEDDING_NORMALIZE,
    HUGGINGFACE_API_KEY,
    HUGGINGFACE_EMBEDDING_MODE,
    LOCAL_MODELS_OFFLINE,
)
from app.services.embedding.errors import EmbeddingAuthError, EmbeddingServerError
from app.services.pipeline_timing import current_timing
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.embedding.hf_endpoint")

_LOCAL_REQUIRED_FILES = (
    "config.json",
    "modules.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "model.safetensors",
)


def _raise_huggingface_error(exc: Exception) -> None:
    detail = str(exc)
    if "401" in detail or "Unauthorized" in detail or "Invalid username or password" in detail:
        raise EmbeddingAuthError(
            "API Key HuggingFace không hợp lệ, đã hết hạn, hoặc không có quyền dùng embedding đã cấu hình. "
            "Vui lòng kiểm tra lại HuggingFace API key trong phần cấu hình."
        ) from exc

    if "500" in detail or "Internal Server Error" in detail or "Server error" in detail:
        raise EmbeddingServerError(
            "Dịch vụ HuggingFace embedding đang lỗi phía máy chủ khi gọi model đã cấu hình. "
            "Vui lòng thử lại sau hoặc chọn cấu hình embedding ổn định hơn."
        ) from exc

    raise EmbeddingServerError(
        f"Không thể tạo embedding bằng HuggingFace model đã cấu hình: {detail}"
    ) from exc


class HuggingFaceEndpointEmbedding:
    """Embedding adapter used by retrieval, ingestion, FAISS and semantic cache."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        api_key: Optional[str] = None,
        mode: str = HUGGINGFACE_EMBEDDING_MODE,
        device: str = EMBEDDING_DEVICE,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        normalize_embeddings: bool = EMBEDDING_NORMALIZE,
        expected_dimension: int = EMBEDDING_DIMENSION,
        local_files_only: bool = LOCAL_MODELS_OFFLINE,
    ):
        self._model_name = model
        self._mode = mode.strip().lower()
        self._device = device
        self._batch_size = batch_size
        self._normalize_embeddings = normalize_embeddings
        self._expected_dimension = expected_dimension
        self._local_files_only = local_files_only
        self._engine = None
        self._engine_lock = threading.Lock()

        if self._batch_size <= 0:
            raise ValueError(f"EMBEDDING_BATCH_SIZE must be greater than 0; got {self._batch_size}.")
        if self._expected_dimension <= 0:
            raise ValueError(f"EMBEDDING_DIMENSION must be greater than 0; got {self._expected_dimension}.")
        
        if self._mode == "api":
            final_api_key = api_key or HUGGINGFACE_API_KEY
            if not final_api_key:
                raise EmbeddingAuthError(
                    "Vui lòng cung cấp API Key HuggingFace trong cấu hình để sử dụng mô hình Embedding qua API."
                )
            logger.info("Đang kết nối mô hình %s qua Hugging Face API...", model)
            self._engine = HuggingFaceEndpointEmbeddings(
                model=model,
                task="feature-extraction",
                huggingfacehub_api_token=final_api_key,
            )
        elif self._mode == "local":
            self._validate_local_artifact()
            if LOCAL_MODELS_OFFLINE:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            logger.info("Local embedding configured: model=%s device=%s", model, device)
        else:
            raise ValueError("HUGGINGFACE_EMBEDDING_MODE must be either 'api' or 'local'.")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def langchain_embeddings(self):
        """Return a LangChain-compatible object for FAISS."""
        return self._engine if self._mode == "api" else self

    def _validate_local_artifact(self) -> None:
        if not self._model_name:
            raise ValueError("HUGGINGFACE_EMBEDDING_MODEL must be a local path when local embedding mode is enabled.")

        model_path = Path(self._model_name)
        if not model_path.exists() or not model_path.is_dir():
            raise FileNotFoundError(
                f"Local embedding model directory does not exist: {model_path}. "
                "Set HUGGINGFACE_EMBEDDING_MODEL to the fine-tuned model directory."
            )

        missing = [name for name in _LOCAL_REQUIRED_FILES if not (model_path / name).exists()]
        if missing:
            raise FileNotFoundError(
                f"Local embedding artifact at {model_path} is missing required files: {', '.join(missing)}."
            )

    def _get_local_engine(self):
        if self._engine is None:
            with self._engine_lock:
                if self._engine is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as exc:  # pragma: no cover - dependency check
                        raise RuntimeError(
                            "sentence-transformers is required for local embedding inference."
                        ) from exc

                    logger.info("Loading local SentenceTransformer from %s", self._model_name)
                    load_start = time.perf_counter_ns()
                    self._engine = SentenceTransformer(
                        self._model_name,
                        device=self._device,
                        local_files_only=self._local_files_only,
                    )
                    if hasattr(self._engine, "eval"):
                        self._engine.eval()
                    collector = current_timing()
                    if collector is not None:
                        collector.mark_embedding_model_load((time.perf_counter_ns() - load_start) / 1_000_000)
        return self._engine

    def _validate_vectors(self, vectors: List[List[float]], expected_count: int) -> List[List[float]]:
        if len(vectors) != expected_count:
            raise RuntimeError(
                f"Embedding output count mismatch: expected {expected_count}, got {len(vectors)}."
            )
        for index, vector in enumerate(vectors):
            if len(vector) != self._expected_dimension:
                raise RuntimeError(
                    f"Embedding dimension mismatch for vector {index}: "
                    f"expected {self._expected_dimension}, got {len(vector)}."
                )
            if not all(math.isfinite(float(value)) for value in vector):
                raise RuntimeError(f"Embedding output contains NaN or Inf at vector {index}.")
        return vectors

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        engine = self._get_local_engine()
        collector = current_timing()
        if collector is not None:
            with collector.stage("query_embedding"):
                vectors = engine.encode(
                    texts,
                    batch_size=self._batch_size,
                    normalize_embeddings=self._normalize_embeddings,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
        else:
            vectors = engine.encode(
                texts,
                batch_size=self._batch_size,
                normalize_embeddings=self._normalize_embeddings,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        if hasattr(vectors, "tolist"):
            vectors = vectors.tolist()
        return self._validate_vectors(vectors, len(texts))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents at once."""
        if self._mode == "local":
            return self._embed_local(texts)

        try:
            vectors = self._engine.embed_documents(texts)
            return self._validate_vectors(vectors, len(texts))
        except Exception as exc:
            _raise_huggingface_error(exc)

    def embed_query(self, text: str) -> List[float]:
        """Embed one query."""
        if self._mode == "local":
            vectors = self._embed_local([text])
            return vectors[0]

        try:
            vector = self._engine.embed_query(text)
            return self._validate_vectors([vector], 1)[0]
        except Exception as exc:
            _raise_huggingface_error(exc)
