"""
Base protocol for context builder modules.
Every context building strategy must implement this interface.
"""
from typing import Protocol, List, Dict, Any, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseContextBuilder(Protocol):
    """Interface for context building strategies.

    Used for ablation studies that compare how context organization affects
    answer quality.
    """

    @property
    def strategy_name(self) -> str:
        """Strategy name used for logging and tracking."""
        ...

    def build(self, documents: List[Document]) -> str:
        """Build an LLM-ready context string from retrieved documents.

        Args:
            documents: Retrieved or reranked documents.

        Returns:
            Context text ready to be injected into the LLM prompt.
        """
        ...

    def format_for_frontend(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Format documents for frontend display.

        Args:
            documents: Documents selected for the answer.

        Returns:
            List of dictionaries containing content and metadata for the UI.
        """
        ...
