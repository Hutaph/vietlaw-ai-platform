import logging
from typing import List, Optional
from langchain_core.documents import Document
from app.services.reranking.base import BaseReranker

logger = logging.getLogger(__name__)

class FallbackReranker(BaseReranker):
    """
    Wrapper để tự động fallback sang mô hình reranker dự phòng nếu mô hình chính bị lỗi.
    Ví dụ: Lỗi OutOfMemory từ CrossEncoder -> Fallback về NoReranker.
    """
    def __init__(self, primary: BaseReranker, secondary: BaseReranker):
        self.primary = primary
        self.secondary = secondary

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        try:
            return self.primary.rerank(query, documents, top_k, api_key=api_key)
        except Exception as e:
            logger.warning(f"Primary reranker failed ({e}). Fallback to secondary...")
            try:
                return self.secondary.rerank(query, documents, top_k, api_key=api_key)
            except Exception as e2:
                logger.error(f"Both primary and secondary rerankers failed. Errors: {e} | {e2}")
                raise RuntimeError("All reranker providers failed.") from e2
