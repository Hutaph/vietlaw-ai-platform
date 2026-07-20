"""
Ollama Embedding — tạo embedding bằng Ollama chạy trên máy local.
"""
import json
from typing import List, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from langchain_core.embeddings import Embeddings

from app.config import (
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    OLLAMA_EMBEDDING_TIMEOUT,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.embedding.ollama")


class OllamaEmbedding(Embeddings):
    """LangChain-compatible embedding provider dùng Ollama REST API."""

    def __init__(
        self,
        model: str = OLLAMA_EMBEDDING_MODEL,
        base_url: str = OLLAMA_BASE_URL,
        timeout: float = OLLAMA_EMBEDDING_TIMEOUT,
    ):
        self._model_name = model
        self._endpoint = f"{base_url.rstrip('/')}/api/embed"
        self._timeout = timeout
        logger.info(
            "Dùng mô hình embedding local %s qua Ollama tại %s",
            model,
            base_url,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def langchain_embeddings(self) -> "OllamaEmbedding":
        """FAISS chỉ cần object có embed_documents và embed_query."""
        return self

    def _embed(self, inputs: Union[str, List[str]]) -> List[List[float]]:
        payload = json.dumps(
            {
                "model": self._model_name,
                "input": inputs,
                "truncate": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=self._timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Ollama embedding failed ({exc.code}): {details}"
            ) from exc
        except URLError as exc:
            raise ConnectionError(
                "Không kết nối được Ollama. Hãy mở Ollama và kiểm tra "
                f"endpoint {self._endpoint}."
            ) from exc

        embeddings = result.get("embeddings")
        if not isinstance(embeddings, list):
            raise RuntimeError("Ollama không trả về trường 'embeddings' hợp lệ.")
        return embeddings

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Nhúng một batch văn bản."""
        if not texts:
            return []

        embeddings = self._embed(texts)
        if len(embeddings) != len(texts):
            raise RuntimeError(
                "Số vector Ollama trả về không khớp số văn bản đầu vào."
            )
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Nhúng một câu truy vấn bằng cùng model dùng khi indexing."""
        embeddings = self._embed(text)
        if not embeddings:
            raise RuntimeError("Ollama không trả về vector cho câu truy vấn.")
        return embeddings[0]
