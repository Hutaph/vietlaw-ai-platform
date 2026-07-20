## Context

The current search architecture uses a Python-based in-memory `rank_bm25` module to perform sparse vector search (BM25 keyword search), which is then manually fused with FAISS or Qdrant dense vector results. As the number of legal clauses grows, loading the entire corpus into RAM to build the BM25 index on backend startup causes memory bloat and scaling limits. Qdrant natively supports Sparse Vectors alongside Dense Vectors and provides a built-in mechanism for Reciprocal Rank Fusion (RRF) when using `prefetch` in the `query_points` API.

## Goals / Non-Goals

**Goals:**
- Offload BM25 sparse vector search from Python RAM to Qdrant.
- Convert Vietnamese legal texts into Sparse Vectors during the ingestion phase.
- Re-architect Qdrant collection to support Named Vectors (Dense + Sparse).
- Implement Qdrant-native Hybrid Search (RRF).

**Non-Goals:**
- We are not implementing advanced deep-learning sparse models (like SPLADE) due to lack of fine-tuned Vietnamese SPLADE models. We will stick to a traditional TF-IDF/BM25 token-counting approach for sparse vectors for now.

## Decisions

1. **Sparse Vector Generation Strategy**:
   - We will write a simple, custom Python Sparse Vector Generator that splits Vietnamese text into tokens (using basic whitespace/punctuation splitting or a library like `pyvi` if available) and calculates word frequencies (Term Frequency).
   - Qdrant's sparse vector expects a dictionary of `{index: integer, value: float}`. We will hash tokens into 32-bit integers using `mmh3` or Python's built-in `hash()` (with a fixed seed or mapping) to generate stable indices, and use term frequency or TF-IDF for the value.

2. **Qdrant Collection Schema**:
   - Recreate the `vietlaw_clauses` collection with two vectors:
     - `text-dense`: size 1024, distance COSINE (for `BAAI/bge-m3`).
     - `text-sparse`: type SPARSE, modifier (if applicable, e.g. IDF).

3. **Search Mechanism**:
   - Use Qdrant's `query_points` method.
   - Define two `prefetch` requests: one for `text-dense` and one for `text-sparse`.
   - Set the main `query` to `FusionQuery(fusion=Fusion.RRF)` to let Qdrant fuse the results efficiently.

## Risks / Trade-offs

- **[Risk]** Data Loss during Migration → We must delete the current collection and completely re-ingest all 5756 clauses. This will take ~45 minutes on CPU.
- **[Trade-off]** BM25 Global IDF computation → Traditional BM25 requires knowing the document frequency of every term across the whole corpus. If we compute Sparse Vectors on-the-fly during chunking, we only have Term Frequency (TF), not Global IDF. Qdrant's sparse vectors can accept raw TF and still perform decently, or we can use Qdrant's experimental IDF modifier features if available. We will start with simple TF (Term Frequency) sparse vectors and let Qdrant handle the sparse indexing.

## Migration Plan

1. Update `backend/app/services/storage.py` to define the Named Vectors schema.
2. Update `ingest_json_documents` to compute and attach sparse vectors during the payload upload.
3. Update `qdrant_search.py` to use `query_points` with RRF fusion.
4. Run the standalone ingest container to recreate the database.
