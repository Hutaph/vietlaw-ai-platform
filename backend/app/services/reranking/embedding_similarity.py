"""
Remote embedding-similarity reranker for deployment-safe reranking.

This is not a cross-encoder. It reuses the deployed HuggingFace embedding stack
to score query/document cosine similarity after retrieval, which keeps reranking
remote-only when Ollama is unavailable.
"""
from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional

from langchain_core.documents import Document

from app.config import EMBEDDING_MODEL, HUGGINGFACE_API_KEY
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.reranking.embedding_similarity")


class HuggingFaceEmbeddingSimilarityReranker:
    """Rerank documents by cosine similarity using HuggingFace embeddings."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        api_key: Optional[str] = None,
        max_candidates: int = 20,
    ):
        self._model = model
        self._api_key = api_key or HUGGINGFACE_API_KEY
        self._max_candidates = max_candidates
        self._embedding_cache: Dict[str, HuggingFaceEndpointEmbedding] = {}
        logger.info("EmbeddingSimilarityReranker initialized with model: %s", model)

    @property
    def strategy_name(self) -> str:
        return f"embedding_similarity({self._model})"

    def _get_embedding(self, api_key: Optional[str] = None):
        resolved_api_key = api_key or self._api_key
        cache_key = (
            hashlib.sha256(resolved_api_key.encode("utf-8")).hexdigest()[:16]
            if resolved_api_key
            else "default"
        )
        if cache_key not in self._embedding_cache:
            self._embedding_cache[cache_key] = HuggingFaceEndpointEmbedding(
                model=self._model,
                api_key=resolved_api_key,
                mode="api",
            )
        return self._embedding_cache[cache_key]

    @staticmethod
    def _cosine(left: List[float], right: List[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        if not documents:
            return []

        embedding = self._get_embedding(api_key)
        query_vector = embedding.embed_query(query)

        candidate_docs = documents[:max(top_k, self._max_candidates)]
        doc_vectors = embedding.embed_documents([doc.page_content for doc in candidate_docs])
        scored_docs = [
            (self._cosine(query_vector, doc_vector), doc)
            for doc, doc_vector in zip(candidate_docs, doc_vectors)
        ]

        scored_docs.sort(key=lambda item: item[0], reverse=True)
        results = [doc for _, doc in scored_docs[:top_k]]
        logger.info(
            "EmbeddingSimilarity reranked %d -> %d documents (top score: %.4f)",
            len(documents),
            len(results),
            scored_docs[0][0] if scored_docs else 0.0,
        )
        return results
