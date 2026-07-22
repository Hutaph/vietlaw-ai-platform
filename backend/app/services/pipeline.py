"""
RAG Pipeline Orchestrator.

Pipeline flow:
    Query → Search → Rerank → Context Build → (LLM)

Components are assembled from configuration to support ablation studies.
"""
import os
import json
import glob
import time
import hashlib
import inspect
from typing import List, Dict, Any, Optional, Tuple

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

from app.config import (
    FAISS_INDEX_PATH, JSON_DATA_PATH, TRACKING_FILE, EMBEDDING_MODEL,
    EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_RETRIES,
    EMBEDDING_SLEEP_BETWEEN_BATCHES, EMBEDDING_RETRY_BASE_WAIT,
    EMBEDDING_PROVIDER, ENABLE_FAISS_FALLBACK, PIPELINE_CONFIG,
    RETRIEVER_CANDIDATE_K, RETRIEVER_K, STORAGE_BACKEND, RUNTIME_PROFILE,
)
from app.services.knowledge_base import load_knowledge_base
from app.services.embedding import (
    BaseEmbedding,
    HuggingFaceEndpointEmbedding,
    OllamaEmbedding,
    FallbackEmbedding,
)
from app.services.embedding.errors import EmbeddingServiceError
from app.services.chunking import ClauseChunker
from app.services.search import FAISSSearcher, QdrantSearcher
from app.services.reranking import (
    NoReranker,
    CrossEncoderReranker,
    HuggingFaceEmbeddingSimilarityReranker,
    FallbackReranker,
)
from app.services.context_builder import NestedContextBuilder
from app.services.pipeline_timing import current_timing
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.pipeline")


class RAGPipeline:
    """Orchestrator that connects Search, Rerank, and Context Builder.

    Each component can be swapped independently for ablation studies.

    Example:
        # Baseline
        pipeline = RAGPipeline(searcher=faiss, reranker=no_reranker, context_builder=nested)

        # + Reranker
        pipeline = RAGPipeline(searcher=faiss, reranker=cross_encoder, context_builder=nested)
    """

    def __init__(self, rewriter, searcher, reranker, context_builder):
        self.rewriter = rewriter
        self.searcher = searcher
        self.reranker = reranker
        self.context_builder = context_builder

        logger.info(
            "RAGPipeline initialized: rewriter=%s, search=%s, reranker=%s, context=%s",
            rewriter.__class__.__name__,
            searcher.strategy_name,
            reranker.strategy_name,
            context_builder.strategy_name,
        )

    def retrieve(
        self,
        query: str,
        k: int = RETRIEVER_CANDIDATE_K,
        rerank_top_k: Optional[int] = None,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        queries: Optional[List[str]] = None,
        enable_reranker: bool = True,
        context_token_budget: Optional[int] = None,
        embedding_api_key: Optional[str] = None,
        reranker_api_key: Optional[str] = None,
    ) -> Tuple[List[Document], str]:
        """Run the full retrieval pipeline: Search → Rerank → Context Build.

        Args:
            query: User question.
            k: Number of candidate documents to retrieve before reranking.
            rerank_top_k: Number of documents kept after reranking (default = RETRIEVER_K).
            category: Optional legal category filter.
            api_key: Embedding API key when a cloud endpoint is used.

        Returns:
            Tuple (documents, context_string).
        """
        final_k = rerank_top_k or RETRIEVER_K

        # Step 0: Rewrite & Route
        if domain is None or queries is None:
            domain, queries = self.rewriter.rewrite(query)
            logger.debug("Rewriter domain: %s, queries: %s", domain, queries)
        
        if domain == "chitchat":
            logger.info("Query routed as chitchat, bypassing retrieval.")
            return [], ""
            
        if not queries:
            queries = [query]

        # Step 1: Search
        # Pass api_key to searchers that support endpoint-backed embedding.
        import inspect
        if "api_key" in inspect.signature(self.searcher.search).parameters:
            docs = self.searcher.search(
                queries,
                k=k,
                category=category,
                api_key=embedding_api_key,
            )
        else:
            docs = self.searcher.search(queries, k=k, category=category)
        retrieved_count = len(docs)
        collector = current_timing()
        if collector is not None:
            collector.set_metric("requested_candidate_k", k)
            collector.set_metric("retrieved_candidate_count", retrieved_count)
            collector.set_metric("retrieved_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
        
        # Deduplicate
        seen = set()
        unique_docs = []
        for doc in docs:
            doc_id = doc.metadata.get("id")
            if doc_id not in seen:
                seen.add(doc_id)
                unique_docs.append(doc)
                
        docs = unique_docs
        dedup_count = len(docs)
        if collector is not None:
            collector.set_metric("deduplicated_candidate_count", dedup_count)
            collector.set_metric("deduplicated_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])

        # Step 2: Rerank or keep search order.
        if enable_reranker:
            rerank_parameters = inspect.signature(self.reranker.rerank).parameters
            if "api_key" in rerank_parameters:
                docs = self.reranker.rerank(
                    query,
                    docs,
                    top_k=final_k,
                    api_key=reranker_api_key,
                )
            else:
                docs = self.reranker.rerank(query, docs, top_k=final_k)
        else:
            docs = docs[:final_k]
        final_count = len(docs)
        if collector is not None:
            collector.set_metric("requested_top_k", final_k)
            collector.set_metric("reranked_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
            collector.set_metric("final_context_count", final_count)
            collector.set_metric("final_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
        
        logger.info(
            "Pipeline retrieve (Sync) [domain=%s, rewritten=%d] -> Search: %d docs -> Dedup: %d docs -> Rerank: %d docs", 
            domain, len(queries), retrieved_count, dedup_count, final_count
        )

        # Step 3: Build context within the configured token budget.
        if collector is not None:
            with collector.stage("context_building"):
                docs, context = self._build_context_with_budget(docs, context_token_budget)
        else:
            docs, context = self._build_context_with_budget(docs, context_token_budget)
        if collector is not None:
            collector.set_metric("final_context_count", len(docs))
            collector.set_metric("final_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])

        return docs, context

    async def aretrieve(
        self,
        query: str,
        k: int = RETRIEVER_CANDIDATE_K,
        rerank_top_k: Optional[int] = None,
        category: Optional[str] = None,
        domain: Optional[str] = None,
        queries: Optional[List[str]] = None,
        enable_reranker: bool = True,
        context_token_budget: Optional[int] = None,
        embedding_api_key: Optional[str] = None,
        reranker_api_key: Optional[str] = None,
    ) -> Tuple[List[Document], str]:
        """Async retrieval variant used by FastAPI endpoints."""
        final_k = rerank_top_k or RETRIEVER_K

        # Step 0: Async Rewrite & Route
        import asyncio
        if domain is None or queries is None:
            domain, queries = await asyncio.to_thread(self.rewriter.rewrite, query)
            logger.debug("Rewriter domain: %s, queries: %s", domain, queries)
        
        if domain == "chitchat":
            logger.info("Query routed as chitchat, bypassing retrieval.")
            return [], ""
            
        if not queries:
            queries = [query]

        # Step 1: Async Search
        import inspect
        if hasattr(self.searcher, "asearch"):
            if "api_key" in inspect.signature(self.searcher.asearch).parameters:
                docs = await self.searcher.asearch(
                    queries,
                    k=k,
                    category=category,
                    api_key=embedding_api_key,
                )
            else:
                docs = await self.searcher.asearch(queries, k=k, category=category)
        else:
            if "api_key" in inspect.signature(self.searcher.search).parameters:
                docs = await asyncio.to_thread(
                    self.searcher.search,
                    queries,
                    k=k,
                    category=category,
                    api_key=embedding_api_key,
                )
            else:
                docs = await asyncio.to_thread(
                    self.searcher.search,
                    queries,
                    k=k,
                    category=category,
                )
        retrieved_count = len(docs)
        collector = current_timing()
        if collector is not None:
            collector.set_metric("requested_candidate_k", k)
            collector.set_metric("retrieved_candidate_count", retrieved_count)
            collector.set_metric("retrieved_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
        
        # Deduplicate
        seen = set()
        unique_docs = []
        for doc in docs:
            doc_id = doc.metadata.get("id")
            if doc_id not in seen:
                seen.add(doc_id)
                unique_docs.append(doc)
                
        docs = unique_docs
        dedup_count = len(docs)
        if collector is not None:
            collector.set_metric("deduplicated_candidate_count", dedup_count)
            collector.set_metric("deduplicated_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])

        # Step 2: Rerank or keep search order.
        if enable_reranker:
            rerank_parameters = inspect.signature(self.reranker.rerank).parameters
            if "api_key" in rerank_parameters:
                docs = self.reranker.rerank(
                    query,
                    docs,
                    top_k=final_k,
                    api_key=reranker_api_key,
                )
            else:
                docs = self.reranker.rerank(query, docs, top_k=final_k)
        else:
            docs = docs[:final_k]
        final_count = len(docs)
        if collector is not None:
            collector.set_metric("requested_top_k", final_k)
            collector.set_metric("reranked_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
            collector.set_metric("final_context_count", final_count)
            collector.set_metric("final_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])
        
        logger.info(
            "Pipeline retrieve (Async) [domain=%s, rewritten=%d] -> Search: %d docs -> Dedup: %d docs -> Rerank: %d docs", 
            domain, len(queries), retrieved_count, dedup_count, final_count
        )

        # Step 3: Build context within the configured token budget.
        if collector is not None:
            with collector.stage("context_building"):
                docs, context = self._build_context_with_budget(docs, context_token_budget)
        else:
            docs, context = self._build_context_with_budget(docs, context_token_budget)
        if collector is not None:
            collector.set_metric("final_context_count", len(docs))
            collector.set_metric("final_source_ids", [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")])

        return docs, context

    def _build_context_with_budget(
        self,
        docs: List[Document],
        token_budget: Optional[int],
    ) -> Tuple[List[Document], str]:
        """Keep complete legal chunks while approximating four characters per token."""
        if not docs or token_budget is None:
            return docs, self.context_builder.build(docs)

        full_context = self.context_builder.build(docs)
        full_tokens = max(1, (len(full_context) + 3) // 4)
        if full_tokens <= token_budget:
            logger.info(
                "Context budget %d tokens kept %d/%d documents (estimated=%d)",
                token_budget,
                len(docs),
                len(docs),
                full_tokens,
            )
            return docs, full_context

        compact_builder = getattr(self.context_builder, "build_compact", None)
        if callable(compact_builder):
            compact_context = compact_builder(docs)
            compact_tokens = max(1, (len(compact_context) + 3) // 4)
            if compact_tokens <= token_budget:
                logger.info(
                    "Context budget %d tokens kept %d/%d documents using compact context (estimated=%d)",
                    token_budget,
                    len(docs),
                    len(docs),
                    compact_tokens,
                )
                return docs, compact_context

        selected: List[Document] = []
        context = ""
        for doc in docs:
            candidate_docs = [*selected, doc]
            candidate_context = self.context_builder.build(candidate_docs)
            estimated_tokens = max(1, (len(candidate_context) + 3) // 4)
            if estimated_tokens <= token_budget or not selected:
                selected = candidate_docs
                context = candidate_context
            else:
                break

        logger.info(
            "Context budget %d tokens kept %d/%d documents (estimated=%d)",
            token_budget,
            len(selected),
            len(docs),
            max(1, (len(context) + 3) // 4) if context else 0,
        )
        return selected, context
    def format_for_frontend(self, docs: List[Document]) -> List[Dict[str, Any]]:
        """Delegate frontend formatting to the active context builder."""
        return self.context_builder.format_for_frontend(docs)


# ---------------------------------------------------------------------------
# FACTORY: initialize the pipeline from config.
# ---------------------------------------------------------------------------

# Module-level state
_embedding_cache: Dict[str, BaseEmbedding] = {}
_pipeline: Optional[RAGPipeline] = None
_faiss_vectorstore: Optional[FAISS] = None


def _get_embedding(api_key: str = None) -> Optional[BaseEmbedding]:
    """Lazy init embedding model, cached by api_key."""
    global _embedding_cache
    
    credential_key = (
        hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        if api_key
        else "default"
    )
    cache_key = f"{RUNTIME_PROFILE}:{credential_key}"
    if cache_key in _embedding_cache:
        return _embedding_cache[cache_key]
        
    try:
        from app.config import INFERENCE_STRATEGY
        hf_emb = HuggingFaceEndpointEmbedding(api_key=api_key)
        
        if INFERENCE_STRATEGY == "local_first":
            ollama_emb = OllamaEmbedding()
            emb = FallbackEmbedding(primary=ollama_emb, secondary=hf_emb)
        else:
            emb = hf_emb
            
        _embedding_cache[cache_key] = emb
        return emb
    except EmbeddingServiceError:
        raise
    except Exception as exc:
        logger.warning("Embedding backend unavailable: %s", exc)
        return None


def _get_processed_files() -> List[str]:
    """Read the list of files that have already been embedded."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def _mark_file_as_processed(filename: str) -> None:
    """Mark a file as processed."""
    processed = _get_processed_files()
    if filename not in processed:
        processed.append(filename)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, ensure_ascii=False, indent=4)


def _embed_single_file(file_path: str, chunker, embedding) -> None:
    """Embed one JSON file into the FAISS index."""
    global _faiss_vectorstore

    filename = os.path.basename(file_path)
    logger.info("=" * 50)
    logger.info("BẮT ĐẦU EMBEDDING: %s", filename)
    logger.info("=" * 50)

    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    # Use the configured chunker to split documents.
    splits = chunker.chunk(raw_data)
    logger.info("Số lượng chunk cần nhúng: %d", len(splits))

    lc_embeddings = embedding.langchain_embeddings

    for i in range(0, len(splits), EMBEDDING_BATCH_SIZE):
        batch = splits[i:i + EMBEDDING_BATCH_SIZE]
        logger.info("  + Đang đẩy batch %d → %d...", i, i + len(batch))

        for attempt in range(EMBEDDING_MAX_RETRIES):
            try:
                if _faiss_vectorstore is None:
                    _faiss_vectorstore = FAISS.from_documents(
                        batch, lc_embeddings,
                        distance_strategy=DistanceStrategy.COSINE
                    )
                else:
                    _faiss_vectorstore.add_documents(batch)

                time.sleep(EMBEDDING_SLEEP_BETWEEN_BATCHES)
                break

            except Exception as e:
                logger.warning(
                    "  -> Lỗi batch %d lần %d/%d: %s",
                    i, attempt + 1, EMBEDDING_MAX_RETRIES, str(e)[:100]
                )
                if attempt < EMBEDDING_MAX_RETRIES - 1:
                    wait_time = EMBEDDING_RETRY_BASE_WAIT * (attempt + 1)
                    logger.info("  -> Tạm nghỉ %ds...", wait_time)
                    time.sleep(wait_time)
                else:
                    logger.error("THẤT BẠI TẠI BATCH %d SAU %d LẦN THỬ.", i, EMBEDDING_MAX_RETRIES)
                    raise e

    _faiss_vectorstore.save_local(FAISS_INDEX_PATH)
    _mark_file_as_processed(filename)
    logger.info("Finished embedding and saved file: %s", filename)


def _init_faiss_index(embedding) -> None:
    """Load the FAISS index from disk without auto-embedding new documents."""
    global _faiss_vectorstore

    lc_embeddings = embedding.langchain_embeddings

    # Load an existing index when available.
    if os.path.exists(FAISS_INDEX_PATH):
        logger.info("Đang tải FAISS Index từ ổ cứng...")
        try:
            _faiss_vectorstore = FAISS.load_local(
                FAISS_INDEX_PATH,
                lc_embeddings,
                allow_dangerous_deserialization=True
            )
            logger.info("FAISS Index đã sẵn sàng.")
        except Exception as e:
            logger.error("Lỗi khi tải FAISS Index: %s", str(e))
            _faiss_vectorstore = None
    else:
        logger.warning(
            "Không tìm thấy FAISS Index tại %s. "
            "Nếu bạn dùng FAISS làm bộ nhớ chính, vui lòng chạy script ingest (nhúng tài liệu) riêng rẽ để tạo index.",
            FAISS_INDEX_PATH
        )
        _faiss_vectorstore = None


def _create_chunker():
    """Create a chunker from config."""
    strategy = PIPELINE_CONFIG.get("chunking", "clause")
    if strategy == "clause":
        return ClauseChunker()
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")


def _create_searcher(embedding) -> Any:
    """Create the configured searcher."""
    global _faiss_vectorstore

    strategy = PIPELINE_CONFIG.get("search", "faiss")

    if STORAGE_BACKEND.lower() in {"qdrant_postgres", "qdrant"}:
        faiss_searcher = FAISSSearcher(vectorstore=_faiss_vectorstore) if ENABLE_FAISS_FALLBACK else None
        if faiss_searcher is None:
            logger.info("FAISS fallback disabled for %s storage backend.", STORAGE_BACKEND)
        else:
            logger.warning(
                "FAISS fallback explicitly enabled for %s. Ensure the FAISS index was built "
                "with the same embedding model as the active Qdrant collection.",
                STORAGE_BACKEND,
            )
        return QdrantSearcher(vectorstore=_faiss_vectorstore, fallback_searcher=faiss_searcher)

    # FAISS searcher is required for FAISS-backed retrieval.
    if _faiss_vectorstore is None:
        raise RuntimeError("FAISS vectorstore chưa được khởi tạo!")

    faiss_searcher = FAISSSearcher(vectorstore=_faiss_vectorstore)

    if strategy == "faiss":
        return faiss_searcher

    else:
        raise ValueError(f"Unknown search strategy: {strategy} (only 'faiss' or Qdrant supported now)")


def _create_reranker():
    """Create the configured reranker."""
    strategy = PIPELINE_CONFIG.get("reranking", "none")
    max_candidates = PIPELINE_CONFIG.get("reranker_max_candidates", 20)
    if RUNTIME_PROFILE == "serverless" and strategy == "cross_encoder":
        logger.warning(
            "Serverless runtime does not support local cross_encoder; "
            "using embedding_similarity reranking instead."
        )
        strategy = "embedding_similarity"
    if strategy == "none":
        return NoReranker()
    elif strategy in {"embedding_similarity", "remote_embedding_similarity"}:
        return HuggingFaceEmbeddingSimilarityReranker(
            model=EMBEDDING_MODEL,
            max_candidates=max_candidates,
        )
    elif strategy == "cross_encoder":
        model = PIPELINE_CONFIG.get(
            "reranker_model",
            "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected",
        )
        return CrossEncoderReranker(
            model=model,
            device=PIPELINE_CONFIG.get("reranker_device", "cpu"),
            batch_size=PIPELINE_CONFIG.get("reranker_batch_size", 8),
            max_length=PIPELINE_CONFIG.get("reranker_max_length", 512),
            fail_open=PIPELINE_CONFIG.get("reranker_fail_open", False),
        )
    else:
        raise ValueError(
            f"Unknown reranking strategy: {strategy} "
            "(supported: none, cross_encoder, embedding_similarity)"
        )


def _create_context_builder():
    """Create the configured context builder."""
    strategy = PIPELINE_CONFIG.get("context_builder", "nested")
    if strategy == "nested":
        return NestedContextBuilder()
    else:
        raise ValueError(f"Unknown context_builder strategy: {strategy}")

def _create_rewriter():
    """Create the configured query rewriter."""
    strategy = PIPELINE_CONFIG.get("rewriter", "none")
    if strategy == "none":
        from app.services.rewriting.no_rewriter import NoOpRewriter
        return NoOpRewriter()
    elif strategy == "llm":
        from app.services.rewriting.llm_rewriter import LLMRewriter
        return LLMRewriter()
    else:
        raise ValueError(f"Unknown rewriter strategy: {strategy}")


# Backward-compatible type import used by legacy annotations.
from typing import Any


def init_pipeline() -> None:
    """Initialize the full pipeline: Knowledge Base → FAISS → Searcher → Pipeline.

    Called from the FastAPI startup flow.
    """
    global _pipeline

    logger.info("=" * 60)
    logger.info("KHỞI TẠO RAG PIPELINE")
    logger.info("Config: %s", PIPELINE_CONFIG)
    logger.info("=" * 60)

    try:
        # 1. Load corpus metadata into memory.
        load_knowledge_base()

        # 2. Initialize embeddings and FAISS only when FAISS-backed storage is active.
        embedding = None
        if STORAGE_BACKEND.lower() not in {"qdrant_postgres", "qdrant", "postgres", "postgresql"}:
            embedding = _get_embedding()
            if embedding is not None:
                _init_faiss_index(embedding)
            else:
                logger.warning("Embedding backend unavailable; pipeline sẽ dùng fallback retrieval cơ bản.")
        else:
            logger.info("Storage backend %s dùng Qdrant/PostgreSQL; bỏ qua khởi tạo FAISS index để tăng tốc startup.", STORAGE_BACKEND)

        # 3. Create components from config.
        searcher = _create_searcher(embedding)
        reranker = _create_reranker()
        context_builder = _create_context_builder()
        rewriter = _create_rewriter()

        # 4. Assemble pipeline
        _pipeline = RAGPipeline(
            rewriter=rewriter,
            searcher=searcher,
            reranker=reranker,
            context_builder=context_builder,
        )

        logger.info("RAG Pipeline đã sẵn sàng!")
    except Exception as exc:
        logger.error("Không thể khởi tạo pipeline đầy đủ: %s", exc)
        logger.warning("Sẽ giữ pipeline ở trạng thái không sẵn sàng cho đến khi request được xử lý.")
        _pipeline = None


def preload_local_models(warmup: bool = False) -> dict:
    """Load cached local embedding/reranker models, optionally running one synthetic warm-up."""
    import time

    from langchain_core.documents import Document

    pipeline = get_pipeline()
    timings = {
        "embedding_load_ms": 0.0,
        "reranker_load_ms": 0.0,
        "embedding_warmup_ms": 0.0,
        "reranker_warmup_ms": 0.0,
    }

    embedding = _get_embedding()
    if embedding is not None and hasattr(embedding, "_get_local_engine"):
        start = time.perf_counter()
        embedding._get_local_engine()  # type: ignore[attr-defined]
        timings["embedding_load_ms"] = (time.perf_counter() - start) * 1000

    reranker = pipeline.reranker
    if hasattr(reranker, "_load"):
        start = time.perf_counter()
        reranker._load()  # type: ignore[attr-defined]
        timings["reranker_load_ms"] = (time.perf_counter() - start) * 1000

    if warmup:
        if embedding is not None:
            start = time.perf_counter()
            embedding.embed_query("kiểm tra hệ thống")
            timings["embedding_warmup_ms"] = (time.perf_counter() - start) * 1000
        if hasattr(reranker, "rerank"):
            start = time.perf_counter()
            reranker.rerank(
                "kiểm tra hệ thống",
                [Document(page_content="nội dung kiểm tra", metadata={"id": "warmup"})],
                top_k=1,
            )
            timings["reranker_warmup_ms"] = (time.perf_counter() - start) * 1000

    timings["total_startup_model_ms"] = sum(timings.values())
    return timings


def get_pipeline() -> RAGPipeline:
    """Return the current pipeline, initializing it lazily when needed."""
    global _pipeline

    if _pipeline is None:
        logger.warning("Pipeline chưa sẵn sàng, đang tự động khởi tạo trên request đầu tiên...")
        init_pipeline()

    if _pipeline is None:
        raise RuntimeError(
            "RAG Pipeline chưa được khởi tạo. "
            "Hãy kiểm tra cấu hình embedding/storage và log startup."
        )
    return _pipeline
