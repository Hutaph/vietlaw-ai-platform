## Why

The current BM25 implementation for Hybrid Search runs entirely in-memory using the Python `rank_bm25` library. This requires loading all documents into RAM on backend startup, which is not scalable. As the database grows to tens of thousands or hundreds of thousands of clauses, this will lead to severe Out-Of-Memory (OOM) crashes and prolonged startup times. We need to offload sparse vector (BM25) storage and querying to Qdrant, which natively supports Sparse Vectors and Reciprocal Rank Fusion (RRF), allowing for robust, infinite scaling and zero RAM footprint on the backend.

## What Changes

- Implement a custom Vietnamese BM25 tokenizer/sparse vector generator in Python to convert text into token frequency arrays.
- Reconfigure the `vietlaw_clauses` Qdrant collection to support "Named Vectors", specifically configuring a `text-dense` vector (Cosine) and a `text-sparse` vector.
- **BREAKING**: Existing Qdrant collection must be deleted and re-ingested because switching from an unnamed single vector to named multi-vectors requires collection recreation.
- Update `QdrantSearcher` to perform native Hybrid Search using `query_points` with multiple `prefetch` blocks (one for Dense, one for Sparse) utilizing Qdrant's internal RRF mechanism.
- Remove the in-memory `BM25Searcher` completely to free up RAM.

## Capabilities

### New Capabilities

- `sparse-vector-generation`: A capability to generate Sparse Vectors (token-to-weight mappings) tailored for the Vietnamese language, converting clauses into sparse embeddings prior to Qdrant ingestion.

### Modified Capabilities

- `vector-storage`: The Qdrant schema needs to be updated to support Named Vectors (Dense + Sparse).
- `retrieval-persistence`: The query logic needs to be updated to leverage Qdrant's native Hybrid Search (`prefetch` with RRF) instead of doing manual in-memory hybrid fusion.
- `document-ingestion`: The ingestion pipeline needs to orchestrate the generation of both Dense and Sparse vectors and payload mapping during vector insertion.

## Impact

- **Affected Systems**: Backend startup logic (removal of in-memory index building), Qdrant collection schema, Search Pipeline components (`QdrantSearcher`), and Ingestion scripts.
- **Dependencies**: May require additional sparse vector libraries or standard tokenizers (like `pyvi` or standard text processing) for BM25 calculation.
- **Data Migration**: All 5756 clauses must be re-ingested.
