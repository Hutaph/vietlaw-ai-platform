"""
No Reranker — Pass-through, giữ nguyên thứ tự từ search.
Dùng làm baseline trong ablation study.
"""
from typing import List, Optional

from langchain_core.documents import Document


class NoReranker:
    """Pass-through reranker — không thay đổi thứ tự documents.

    Đây là baseline: chỉ cắt tại top_k mà không xếp hạng lại.
    Dùng để so sánh với các reranking strategies thực sự.
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
        """Trả về documents giữ nguyên, chỉ cắt tại top_k."""
        return documents[:top_k]
