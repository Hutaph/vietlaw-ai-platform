"""
Search module for retrieving relevant documents.

Protocol:
    BaseSearcher: shared interface for search strategies.

Implementations:
    - FAISSSearcher: FAISS vector similarity search.
    - QdrantSearcher: Qdrant dense/sparse retrieval.
"""
from app.services.search.base import BaseSearcher
from app.services.search.faiss_search import FAISSSearcher
from app.services.search.qdrant_search import QdrantSearcher

__all__ = ["BaseSearcher", "FAISSSearcher", "QdrantSearcher"]
