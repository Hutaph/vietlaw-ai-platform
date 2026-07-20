## Context
Currently, the `semantic_cache` intercepts queries right after rewriting. Because the cache relies only on similarity matching, it returns historical answers even if the underlying legal documents used to generate those answers have changed. A robust invalidation strategy is required to eliminate stale answers gracefully when the database changes. Qdrant supports complex array-based filtering using `MatchAny`, making it the perfect mechanism to track document IDs.

## Goals / Non-Goals

**Goals:**
- Implement metadata tracking (`retrieved_doc_ids`) in the cache payload to link queries to specific documents.
- Design an invalidation script/method that purges cache entries associated with updated/deleted documents.
- Achieve "Surgical Strike" precision (only deleting cache entries affected by the change).

**Non-Goals:**
- Do not implement a real-time event listener or webhook yet; the purge will be executed synchronously or via manual trigger from the ingest script.
- Do not modify how FAISS/Qdrant retrievers fetch documents.

## Decisions

**Decision 1: Store `retrieved_doc_ids` as an Array in Qdrant Payload**
- *Why?* Qdrant supports inverted indices on arrays. When `MatchAny` is executed, Qdrant can instantly retrieve and delete affected cache points.
- *Alternative considered:* Track `cited_doc_ids` directly parsed from the LLM output. This is fragile since the LLM might hallucinate citations or miss citing something it actually used. Storing the retrieved context document IDs is safer and deterministic.

**Decision 2: Using the Ingest Script for Cache Purge**
- *Why?* The ingest script (`ingest_to_storage.py` or similar) is the single source of truth that knows exactly which `doc_ids` are being overwritten or deleted. Exposing a purge function in the cache utility that the ingest script calls is the cleanest integration point.

## Risks / Trade-offs
- **Risk:** Existing cache entries do not have `retrieved_doc_ids` in their payload.
  - *Mitigation:* The invalidation script will only delete entries where the array exists and matches. A one-time global purge can be run during deployment of this feature to clear the old schema cache.
- **Risk:** High memory/storage overhead in Qdrant payloads.
  - *Mitigation:* `doc_ids` are lightweight strings. An array of ~5-10 IDs per cache point takes negligible space.
