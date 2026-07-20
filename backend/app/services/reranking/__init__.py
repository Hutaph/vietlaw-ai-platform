"""
Reranking Module — Strategies cho việc xếp hạng lại kết quả search.

Protocol:
    BaseReranker: Interface chung cho tất cả reranking strategies.

Implementations:
    - NoReranker: Pass-through (không rerank, giữ nguyên thứ tự)
    - CrossEncoderReranker: Dùng cross-encoder model để rerank
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
