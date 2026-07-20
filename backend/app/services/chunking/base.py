"""
Base Protocol cho Chunking module.
Mọi chunking strategy đều phải implement interface này.
"""
from typing import Protocol, List, Dict, Any, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseChunker(Protocol):
    """Interface cho document chunking strategies.

    Dùng để ablation study: so sánh hiệu quả của các chiến lược chunking
    khác nhau (per-clause, recursive split, semantic chunking, v.v.).
    """

    @property
    def strategy_name(self) -> str:
        """Tên strategy để logging và tracking."""
        ...

    def chunk(self, raw_data: Dict[str, Any]) -> List[Document]:
        """Tách một file JSON luật thành danh sách Document chunks.

        Args:
            raw_data: Dữ liệu JSON đã parse, chứa 'law_info' và 'clauses'.

        Returns:
            Danh sách Document, mỗi document có page_content và metadata.
        """
        ...
