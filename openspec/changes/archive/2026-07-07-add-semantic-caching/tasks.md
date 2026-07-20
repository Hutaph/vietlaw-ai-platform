## 1. Configuration Setup

- [x] 1.1 Add `SEMANTIC_CACHE_THRESHOLD` (default 0.95) and `ENABLE_SEMANTIC_CACHE` (default true) to `.env.example`
- [x] 1.2 Update `backend/app/config.py` to load and expose the new cache configuration variables

## 2. Storage Setup

- [x] 2.1 Update Qdrant initialization logic (in `storage.py` or equivalent startup script) to create a `semantic_cache` collection if it does not exist
- [x] 2.2 Ensure the `semantic_cache` collection uses the same vector dimension as the embedding model being used

## 3. Core Implementation

- [x] 3.1 Create a new service `backend/app/services/semantic_cache.py`
- [x] 3.2 Implement `check_cache(query_vector)` to search the `semantic_cache` collection with similarity threshold filtering
- [x] 3.3 Implement `update_cache(query_vector, original_query, response_text, context_used)` to insert new records into Qdrant

## 4. Pipeline Integration

- [x] 4.1 Update `backend/app/api/chat.py` to intercept the query after the rewriting phase
- [x] 4.2 In `chat.py`, generate the embedding for the rewritten query and call `check_cache()`
- [x] 4.3 If a cache hit occurs, format and return the cached `response_text` and `contextUsed`, bypassing the LLM
- [x] 4.4 If a cache miss occurs, proceed with the normal pipeline and finally call `update_cache()` before returning the response

## 5. Maintenance Scripts (Optional but Recommended)

- [x] 5.1 Create a script `backend/scripts/clear_semantic_cache.py` to flush the `semantic_cache` collection when the knowledge base is updated
