"""
Base protocol for embedding modules.
Every embedding strategy must implement this interface.
"""
from typing import Protocol, List, runtime_checkable


@runtime_checkable
class BaseEmbedding(Protocol):
    """Interface for embedding models.

    Used for ablation studies that swap embedding models without changing the
    pipeline code.
    """

    @property
    def model_name(self) -> str:
        """Model name used for logging and tracking."""
        ...

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents at once for indexing."""
        ...

    def embed_query(self, text: str) -> List[float]:
        """Embed one query for retrieval."""
        ...
