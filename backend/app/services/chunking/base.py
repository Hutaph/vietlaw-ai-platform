"""
Base protocol for chunking modules.
Every chunking strategy must implement this interface.
"""
from typing import Protocol, List, Dict, Any, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseChunker(Protocol):
    """Interface for document chunking strategies.

    Used for ablation studies across per-clause, recursive, and semantic
    chunking strategies.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy name used for logging and tracking."""
        ...

    def chunk(self, raw_data: Dict[str, Any]) -> List[Document]:
        """Split one parsed legal JSON document into chunks.

        Args:
            raw_data: Parsed JSON containing 'law_info' and 'clauses'.

        Returns:
            Documents with page_content and metadata.
        """
        ...
