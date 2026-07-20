"""
Qdrant-backed searcher for legal clause retrieval.

This implementation uses Qdrant. A FAISS fallback can be injected explicitly,
but the default runtime should fail clearly instead of querying a stale index.
"""
from __future__ import annotations

import re
from typing import List, Optional, Union

from langchain_core.documents import Document

from app.config import (
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
    QDRANT_URL,
    RETRIEVER_K,
)
from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding
from app.services.embedding.ollama import OllamaEmbedding
from app.services.embedding.errors import EmbeddingServiceError
from app.services.pipeline_timing import current_timing
from app.services.knowledge_base import (
    ALL_LAWS_CATEGORY,
    document_matches_category,
    normalize_category,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.qdrant")

NORMAL_PREFETCH_MULTIPLIER = 2
EXPLICIT_CITATION_PREFETCH_MULTIPLIER = 4
_EXPLICIT_LEGAL_CITATION_RE = re.compile(
    r"(?i)(?:\bđiều\s*\.?\s*\d+|\bkhoản\s*\.?\s*\d+|\bđiểm\s*\.?\s*[a-zA-Z0-9]\b|\bđ\s*\.?\s*\d+|\bk\s*\.?\s*\d+)"
)


def contains_explicit_legal_citation(query: str) -> bool:
    """Return true for high-confidence Vietnamese legal article/clause references."""
    return bool(_EXPLICIT_LEGAL_CITATION_RE.search(query or ""))


class QdrantSearcher:
    """Vector search using Qdrant with an optional explicitly configured fallback."""

    def __init__(
        self,
        vectorstore,
        fallback_searcher=None,
        collection_name: str = QDRANT_COLLECTION,
    ):
        self._vectorstore = vectorstore
        self._fallback_searcher = fallback_searcher
        self._collection_name = collection_name
        self._client = None

    @property
    def strategy_name(self) -> str:
        return "qdrant"

    @staticmethod
    def _prefetch_limit_for_queries(queries: List[str], k: int) -> int:
        base_limit = max(k, k * NORMAL_PREFETCH_MULTIPLIER)
        if any(contains_explicit_legal_citation(query) for query in queries):
            return max(base_limit, k * EXPLICIT_CITATION_PREFETCH_MULTIPLIER)
        return base_limit

    def _get_embedding_backend(self, api_key: Optional[str] = None):
        from app.config import EMBEDDING_PROVIDER, INFERENCE_STRATEGY

        if EMBEDDING_PROVIDER == "ollama":
            if INFERENCE_STRATEGY != "local_first":
                raise EmbeddingServiceError(
                    "Cấu hình embedding không hợp lệ: remote_first không được dùng Ollama local. "
                    "Vui lòng dùng HuggingFace embedding hoặc chuyển INFERENCE_STRATEGY=local_first."
                )
            return OllamaEmbedding()
            
        from app.services.pipeline import _get_embedding
        emb = _get_embedding(api_key)
        if emb is None:
            raise EmbeddingServiceError(
                "Embedding backend is unavailable for the active runtime profile."
            )
        return emb

    def _get_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
            except ImportError as exc:  # pragma: no cover - runtime dependency check
                raise RuntimeError("qdrant-client is not installed") from exc

            self._client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        return self._client

    def _build_filter(self, category: Optional[str]):
        normalized_category = normalize_category(category)
        if normalized_category == ALL_LAWS_CATEGORY:
            return None

        try:
            from qdrant_client.http import models as qdrant_models
        except ImportError:  # pragma: no cover - runtime dependency check
            return None

        if normalized_category.upper() in ["LKDBDS_2023", "LTTPHS_2025", "LNO_2023", "LBVMT_2020", "LXD_2014", "LDD_2024", "LCC_2024", "BLTTDS_2015"]:
            return qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="law_id",
                        match=qdrant_models.MatchValue(value=normalized_category.upper()),
                    )
                ]
            )

        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="category",
                    match=qdrant_models.MatchValue(value=normalized_category),
                )
            ]
        )

    def _search_qdrant(self, query: Union[str, List[str]], k: int, category: Optional[str], api_key: Optional[str] = None) -> List[Document]:
        embedding_backend = self._get_embedding_backend(api_key)
        
        try:
            from app.services.sparse_vector import SparseVectorGenerator
            sparse_generator = SparseVectorGenerator()
        except ImportError:
            sparse_generator = None

        try:
            from qdrant_client.http import models as qdrant_models
        except ImportError:  # pragma: no cover - runtime dependency check
            logger.warning("qdrant_client models import failed")
            raise

        client = self._get_client()
        query_filter = self._build_filter(category)
        
        queries = [query] if isinstance(query, str) else query
        
        prefetch = []
        prefetch_limit = self._prefetch_limit_for_queries(queries, k)
        for q in queries:
            query_dense_vector = embedding_backend.embed_query(q)
            prefetch.append(
                qdrant_models.Prefetch(
                    query=query_dense_vector,
                    using="text-dense",
                    limit=prefetch_limit,
                    filter=query_filter,
                )
            )
            
            if sparse_generator:
                try:
                    query_sparse_dict = sparse_generator.generate_sparse_vector(q)
                    if query_sparse_dict and query_sparse_dict.get("indices"):
                        prefetch.append(
                            qdrant_models.Prefetch(
                                query=qdrant_models.SparseVector(
                                    indices=query_sparse_dict["indices"],
                                    values=query_sparse_dict["values"]
                                ),
                                using="text-sparse",
                                limit=prefetch_limit,
                                filter=query_filter,
                            )
                        )
                except Exception as exc:
                    logger.warning("Sparse vector generation failed for query '%s': %s", q, exc)

        collector = current_timing()
        stage = collector.stage("qdrant_search") if collector is not None else None
        if stage is None:
            results = self._execute_qdrant_query(client, qdrant_models, prefetch, query, k, query_filter, embedding_backend)
            documents = self._points_to_documents(results)
        else:
            with stage:
                results = self._execute_qdrant_query(client, qdrant_models, prefetch, query, k, query_filter, embedding_backend)
                documents = self._points_to_documents(results)
        return documents

    def _execute_qdrant_query(self, client, qdrant_models, prefetch, query, k, query_filter, embedding_backend):
        try:
            # Bypass Qdrant 1.10 query_points Fusion bug by using query_batch_points and manual RRF
            if len(prefetch) > 1:
                requests = []
                for p in prefetch:
                    req = qdrant_models.QueryRequest(
                        query=p.query,
                        using=p.using,
                        filter=p.filter,
                        limit=p.limit,
                        with_payload=True
                    )
                    requests.append(req)

                batch_results = client.query_batch_points(
                    collection_name=self._collection_name,
                    requests=requests
                )

                # Manual RRF Fusion
                rrf_scores = {}
                doc_map = {}
                for response in batch_results:
                    for rank, point in enumerate(response.points):
                        doc_map[point.id] = point
                        rrf_scores[point.id] = rrf_scores.get(point.id, 0.0) + 1.0 / (60 + rank + 1)

                # Sort by score descending and take top k
                sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:k]
                return [doc_map[doc_id] for doc_id in sorted_ids]

            if len(prefetch) == 1:
                p = prefetch[0]
                return client.query_points(
                    collection_name=self._collection_name,
                    query=p.query,
                    using=p.using,
                    query_filter=p.filter,
                    limit=p.limit,
                    with_payload=True
                ).points

            return []
        except AttributeError:
            # Fallback for older qdrant-client versions
            if not isinstance(query, str):
                query = query[0] if query else ""
            query_dense_vector = embedding_backend.embed_query(query)
            return client.search(
                collection_name=self._collection_name,
                query_vector=("text-dense", query_dense_vector),
                limit=k,
                query_filter=query_filter,
                with_payload=True,
            )

    @staticmethod
    def _points_to_documents(results) -> List[Document]:
        documents: List[Document] = []
        for point in results:
            payload = point.payload or {}
            metadata = {
                "id": payload.get("id", point.id),
                "law_id": payload.get("law_id"),
                "category": payload.get("category"),
            }
            documents.append(
                Document(page_content=payload.get("content", ""), metadata=metadata)
            )
        return documents

    def search(
        self,
        query: Union[str, List[str]],
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        try:
            return self._search_qdrant(query, k=k, category=category, api_key=api_key)
        except EmbeddingServiceError:
            raise
        except Exception as exc:
            if self._fallback_searcher is not None:
                logger.warning(
                    "Qdrant retrieval failed for collection %s; FAISS fallback is explicitly enabled: %s",
                    self._collection_name,
                    type(exc).__name__,
                )
                import inspect
                if "api_key" in inspect.signature(self._fallback_searcher.search).parameters:
                    return self._fallback_searcher.search(query, k=k, category=category, api_key=api_key)
                return self._fallback_searcher.search(query, k=k, category=category)
            logger.error(
                "Qdrant retrieval failed for collection %s and FAISS fallback is disabled: %s",
                self._collection_name,
                type(exc).__name__,
            )
            raise RuntimeError(
                f"Qdrant retrieval failed for collection {self._collection_name}; "
                "FAISS fallback is disabled."
            ) from exc

    async def asearch(
        self,
        query: Union[str, List[str]],
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        import asyncio
        try:
            return await asyncio.to_thread(self._search_qdrant, query, k, category, api_key)
        except EmbeddingServiceError:
            raise
        except Exception as exc:
            if self._fallback_searcher is not None:
                logger.warning(
                    "Qdrant async retrieval failed for collection %s; FAISS fallback is explicitly enabled: %s",
                    self._collection_name,
                    type(exc).__name__,
                )
                import inspect
                if hasattr(self._fallback_searcher, "asearch"):
                    if "api_key" in inspect.signature(self._fallback_searcher.asearch).parameters:
                        return await self._fallback_searcher.asearch(query, k=k, category=category, api_key=api_key)
                    return await self._fallback_searcher.asearch(query, k=k, category=category)
                if "api_key" in inspect.signature(self._fallback_searcher.search).parameters:
                    return self._fallback_searcher.search(query, k=k, category=category, api_key=api_key)
                return self._fallback_searcher.search(query, k=k, category=category)
            logger.error(
                "Qdrant async retrieval failed for collection %s and FAISS fallback is disabled: %s",
                self._collection_name,
                type(exc).__name__,
            )
            raise RuntimeError(
                f"Qdrant retrieval failed for collection {self._collection_name}; "
                "FAISS fallback is disabled."
            ) from exc
