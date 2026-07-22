import logging
from typing import List
from app.services.embedding.base import BaseEmbedding

logger = logging.getLogger(__name__)

class FallbackEmbedding(BaseEmbedding):
    """
    Wrapper that falls back to a secondary embedding provider when primary fails.
    """
    def __init__(self, primary: BaseEmbedding, secondary: BaseEmbedding):
        self.primary = primary
        self.secondary = secondary

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            return self.primary.embed_documents(texts)
        except Exception as e:
            logger.warning(f"Primary embedding failed ({e}). Fallback to secondary...")
            try:
                return self.secondary.embed_documents(texts)
            except Exception as e2:
                logger.error(f"Both primary and secondary embeddings failed. Errors: {e} | {e2}")
                raise RuntimeError("All embedding providers failed.") from e2

    def embed_query(self, text: str) -> List[float]:
        try:
            return self.primary.embed_query(text)
        except Exception as e:
            logger.warning(f"Primary embedding failed ({e}). Fallback to secondary...")
            try:
                return self.secondary.embed_query(text)
            except Exception as e2:
                logger.error(f"Both primary and secondary embeddings failed. Errors: {e} | {e2}")
                raise RuntimeError("All embedding providers failed.") from e2
