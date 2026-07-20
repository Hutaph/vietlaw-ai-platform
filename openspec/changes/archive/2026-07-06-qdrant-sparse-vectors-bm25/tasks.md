## 1. Qdrant Schema Update

- [x] 1.1 Update `backend/app/services/storage.py` to define Named Vectors (`text-dense` and `text-sparse`) for the `vietlaw_clauses` collection during initialization.
- [x] 1.2 Modify schema checking logic to enforce recreation if the collection exists but does not have named vectors.

## 2. Sparse Vector Generator

- [x] 2.1 Create a new module `backend/app/services/sparse_vector.py`.
- [x] 2.2 Implement a class `SparseVectorGenerator` that tokenizes Vietnamese text (using a basic split or standard library) and calculates Term Frequencies (TF).
- [x] 2.3 Implement hashing logic inside `SparseVectorGenerator` to map tokens to stable 32-bit integer indices.

## 3. Ingestion Pipeline Update

- [x] 3.1 Update `backend/scripts/ingest_to_storage.py` (or the underlying `ingest_json_documents` function in `storage.py`) to initialize `SparseVectorGenerator`.
- [x] 3.2 Modify the batch upsert logic to generate both `text-dense` (from HuggingFace) and `text-sparse` (from generator) for each document before upserting to Qdrant.

## 4. Search Implementation

- [x] 4.1 Update `backend/app/services/search/qdrant_search.py` to modify `_search_qdrant`.
- [x] 4.2 Replace single vector query with `query_points` utilizing two `prefetch` clauses (one for dense, one for sparse).
- [x] 4.3 Configure `FusionQuery(fusion=Fusion.RRF)` in the query logic.
- [x] 4.4 Remove `backend/app/services/search/bm25_search.py` and decouple it from `RAGPipeline` (in `backend/app/services/pipeline.py`) to completely eliminate the RAM-based indexing.

## 5. End-to-End Migration & Testing

- [x] 5.1 Run the ingestion script to populate Qdrant with the new Named Vectors.
- [x] 5.2 Execute a sample hybrid query through the API to verify RRF returns results without crashing.
