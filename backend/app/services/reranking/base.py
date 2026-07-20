"""
Base Protocol cho Reranking module.
Mọi reranking strategy đều phải implement interface này.
"""
from typing import Protocol, List, Optional, runtime_checkable

from langchain_core.documents import Document


@runtime_checkable
class BaseReranker(Protocol):
    """Interface cho reranking strategies.

    Dùng để ablation study: đánh giá tác động của reranking
    lên chất lượng retrieval (ví dụ: no-rerank vs cross-encoder).
    """

    @property
    def strategy_name(self) -> str:
        """Tên strategy để logging và tracking."""
        ...

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        """Xếp hạng lại danh sách documents theo độ liên quan với query.

        Args:
            query: Câu hỏi gốc của người dùng.
            documents: Danh sách Document từ search step.
            top_k: Số lượng document trả về sau reranking.

        Returns:
            Danh sách Document đã được xếp hạng lại, cắt tại top_k.
        """
        ...
