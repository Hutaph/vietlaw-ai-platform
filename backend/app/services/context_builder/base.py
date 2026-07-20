"""
Base Protocol cho Context Builder module.
Mọi context building strategy đều phải implement interface này.
"""
from typing import Protocol, List, Dict, Any, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseContextBuilder(Protocol):
    """Interface cho context building strategies.

    Dùng để ablation study: so sánh cách tổ chức context
    ảnh hưởng thế nào đến chất lượng câu trả lời của LLM.
    """

    @property
    def strategy_name(self) -> str:
        """Tên strategy để logging và tracking."""
        ...

    def build(self, documents: List[Document]) -> str:
        """Xây dựng chuỗi context từ danh sách Document.

        Args:
            documents: Danh sách Document đã retrieved/reranked.

        Returns:
            Chuỗi context text sẵn sàng feed vào LLM prompt.
        """
        ...

    def format_for_frontend(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Định dạng dữ liệu để Frontend hiển thị.

        Args:
            documents: Danh sách Document.

        Returns:
            Danh sách dict chứa content + metadata cho UI.
        """
        ...
