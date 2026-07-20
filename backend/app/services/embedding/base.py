"""
Base Protocol cho Embedding module.
Mọi embedding strategy đều phải implement interface này.
"""
from typing import Protocol, List, runtime_checkable


@runtime_checkable
class BaseEmbedding(Protocol):
    """Interface cho embedding models.

    Dùng để ablation study: swap giữa các embedding model
    (HuggingFace API, local SentenceTransformer, OpenAI, v.v.)
    mà không cần thay đổi pipeline code.
    """

    @property
    def model_name(self) -> str:
        """Tên model để logging và tracking."""
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Nhúng nhiều văn bản cùng lúc (dùng khi indexing)."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Nhúng một câu hỏi (dùng khi search)."""
        ...
