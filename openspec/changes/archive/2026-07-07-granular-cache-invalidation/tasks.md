## 1. Payload Schema Update

- [x] 1.1 In `backend/app/services/cache.py` (or the equivalent file managing the semantic cache), update the `SemanticCache` point insertion logic to include a new array field `retrieved_doc_ids` in the payload.
- [x] 1.2 In `backend/app/api/chat.py` (both streaming and non-streaming endpoints), modify the `update_cache` (or equivalent) call during a Cache Miss to pass `[doc.metadata.get("id", "")] for doc in docs` as an argument.

## 2. Invalidation Logic Implementation

- [x] 2.1 In `backend/app/services/cache.py`, implement a new function `invalidate_cache_by_doc_ids(doc_ids: List[str])` that uses the Qdrant client to delete points in the `semantic_cache` collection where `retrieved_doc_ids` matches any of the provided `doc_ids` using `MatchAny`.
- [x] 2.2 Expose `invalidate_cache_by_doc_ids` so that it can be invoked by external scripts or an internal admin API endpoint.

## 3. Ingest Script Integration

- [x] 3.1 Update the database ingestion script (`backend/ingest_to_storage.py` or equivalent) to collect all document IDs being modified or deleted during a data sync.
- [x] 3.2 Add a step at the end of the ingest script to call the cache invalidation function with the collected document IDs, ensuring old cache points are safely purged.

## 4. Testing

- [x] 4.1 Write a test script `test_cache_invalidation.py` to populate the cache with a mock query and `retrieved_doc_ids`, then call the invalidation function and assert that the cache point is successfully deleted.
- [x] 4.2 Verify that other cache entries with unrelated document IDs are not deleted during the invalidation process.
