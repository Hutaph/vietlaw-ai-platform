"""
FAISS search implementation.
Used for local fallback paths and legacy FAISS-backed retrieval.
"""
from typing import List, Optional, Union

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from app.config import RETRIEVER_K, RETRIEVER_FETCH_K, RETRIEVER_LAMBDA_MULT
from app.services.knowledge_base import (
    ALL_LAWS_CATEGORY,
    document_matches_category,
    normalize_category,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.search.faiss")


class FAISSSearcher:
    """Vector similarity search using FAISS.

    Uses MMR to balance relevance and diversity.
    """

    def __init__(
        self,
        vectorstore: FAISS,
        fetch_k: int = RETRIEVER_FETCH_K,
        lambda_mult: float = RETRIEVER_LAMBDA_MULT,
    ):
        self._vectorstore = vectorstore
        self._fetch_k = fetch_k
        self._lambda_mult = lambda_mult

    @property
    def strategy_name(self) -> str:
        return "faiss_mmr"

    @property
    def vectorstore(self) -> FAISS:
        """Return the FAISS vector store used for indexing and retrieval."""
        return self._vectorstore

    def _lazy_load_vectorstore(self, api_key: Optional[str] = None) -> None:
        if self._vectorstore is not None:
            return

        import os
        from app.config import FAISS_INDEX_PATH
        from app.services.pipeline import _get_embedding
        
        if os.path.exists(FAISS_INDEX_PATH):
            try:
                embedding = _get_embedding(api_key)
                if embedding is not None:
                    logger.info("Lazy loading FAISS index from disk for fallback retrieval...")
                    self._vectorstore = FAISS.load_local(
                        FAISS_INDEX_PATH,
                        embedding.langchain_embeddings,
                        allow_dangerous_deserialization=True
                    )
            except Exception as e:
                logger.warning("Could not lazy load FAISS index: %s", e)
    def search(
        self,
        query: Union[str, List[str]],
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        """Search the FAISS index with MMR."""
        self._lazy_load_vectorstore(api_key)
        if self._vectorstore is None:
            logger.warning("FAISS vectorstore is not initialized; returning empty results")
            return []

        search_kwargs = {
            "k": k,
            "fetch_k": max(self._fetch_k, k),
            "lambda_mult": self._lambda_mult,
        }

        normalized_category = normalize_category(category)
        if normalized_category != ALL_LAWS_CATEGORY:
            search_kwargs["filter"] = (
                lambda metadata: document_matches_category(
                    metadata,
                    normalized_category,
                )
            )

        retriever = self._vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )
        
        queries = [query] if isinstance(query, str) else query
        all_docs = []
        seen = set()
        for q in queries:
            docs = retriever.invoke(q)
            for d in docs:
                doc_id = d.metadata.get("id")
                if doc_id not in seen:
                    seen.add(doc_id)
                    all_docs.append(d)
        return all_docs

    async def asearch(
        self,
        query: Union[str, List[str]],
        k: int = RETRIEVER_K,
        category: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> List[Document]:
        """Async variant used by FastAPI endpoints."""
        self._lazy_load_vectorstore(api_key)
        if self._vectorstore is None:
            logger.warning("FAISS vectorstore is not initialized; returning empty results")
            return []

        search_kwargs = {
            "k": k,
            "fetch_k": max(self._fetch_k, k),
            "lambda_mult": self._lambda_mult,
        }

        normalized_category = normalize_category(category)
        if normalized_category != ALL_LAWS_CATEGORY:
            search_kwargs["filter"] = (
                lambda metadata: document_matches_category(
                    metadata,
                    normalized_category,
                )
            )

        retriever = self._vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs,
        )
        
        queries = [query] if isinstance(query, str) else query
        all_docs = []
        seen = set()
        for q in queries:
            docs = await retriever.ainvoke(q)
            for d in docs:
                doc_id = d.metadata.get("id")
                if doc_id not in seen:
                    seen.add(doc_id)
                    all_docs.append(d)
        return all_docs
