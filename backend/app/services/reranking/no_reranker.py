"""
No Reranker.
Pass-through baseline that preserves the search result order.
"""
from typing import List, Optional

from langchain_core.documents import Document


class NoReranker:
    """Pass-through reranker that does not reorder documents.

    This baseline only truncates to top_k and is used for comparison against
    actual reranking strategies.
    """

    @property
    def strategy_name(self) -> str:
        return "none"

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        """Return documents in the original order, truncated to top_k."""
        return documents[:top_k]
