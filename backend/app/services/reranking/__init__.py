"""
Reranking module for reordering search candidates.

Protocol:
    BaseReranker: shared interface for reranking strategies.

Implementations:
    - NoReranker: pass-through baseline.
    - CrossEncoderReranker: local cross-encoder reranker.
    - HuggingFaceEmbeddingSimilarityReranker: remote embedding-similarity reranker.
"""
from app.services.reranking.base import BaseReranker
from app.services.reranking.no_reranker import NoReranker
from app.services.reranking.cross_encoder import CrossEncoderReranker
from app.services.reranking.embedding_similarity import HuggingFaceEmbeddingSimilarityReranker
from app.services.reranking.fallback import FallbackReranker

__all__ = [
    "BaseReranker",
    "NoReranker",
    "CrossEncoderReranker",
    "HuggingFaceEmbeddingSimilarityReranker",
    "FallbackReranker",
]
