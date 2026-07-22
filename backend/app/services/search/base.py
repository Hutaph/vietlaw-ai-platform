"""
Base protocol for search modules.
Every search strategy must implement this interface.
"""
from typing import Protocol, List, Optional, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseSearcher(Protocol):
    """Interface for document search and retrieval strategies.

    Used for ablation studies across vector search, BM25, hybrid search, etc.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy name used for logging and tracking."""
        ...

    def search(
        self,
        query: str,
        k: int = 6,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Search for documents related to the query.

        Args:
            query: User question or query.
            k: Number of results to return.
            category: Optional legal category filter.

        Returns:
            Documents ranked by relevance.
        """
        ...

    async def asearch(
        self,
        query: str,
        k: int = 6,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Async search variant."""
        ...
