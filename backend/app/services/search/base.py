"""
Base Protocol cho Search module.
Mọi search strategy đều phải implement interface này.
"""
from typing import Protocol, List, Optional, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseSearcher(Protocol):
    """Interface cho document search/retrieval strategies.

    Dùng để ablation study: so sánh vector search, BM25, hybrid, v.v.
    """

    @property
    def strategy_name(self) -> str:
        """Tên strategy để logging và tracking."""
        ...

    def search(
        self,
        query: str,
        k: int = 6,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Tìm kiếm tài liệu liên quan đến câu truy vấn.

        Args:
            query: Câu hỏi / truy vấn của người dùng.
            k: Số lượng kết quả trả về.
            category: Lọc theo lĩnh vực luật (None = không lọc).

        Returns:
            Danh sách Document được xếp hạng theo độ liên quan.
        """
        ...

    async def asearch(
        self,
        query: str,
        k: int = 6,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Async version của search."""
        ...
