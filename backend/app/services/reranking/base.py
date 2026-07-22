"""
Base protocol for reranking modules.
Every reranking strategy must implement this interface.
"""
from typing import Protocol, List, Optional, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseReranker(Protocol):
    """Interface for reranking strategies.

    Used for ablation studies that compare the retrieval impact of no-rerank,
    cross-encoder reranking, and embedding-similarity reranking.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy name used for logging and tracking."""
        ...

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        """Rerank documents by relevance to the query.

        Args:
            query: Original user question.
            documents: Documents from the search step.
            top_k: Number of documents to keep after reranking.

        Returns:
            Reranked documents truncated to top_k.
        """
        ...
