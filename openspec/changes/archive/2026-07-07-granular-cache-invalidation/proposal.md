## Why
In a legal QA system, serving outdated laws due to semantic caching is a critical risk. If a law is updated or replaced, existing cache entries containing old answers become a liability. A Granular Cache Invalidation strategy ensures that whenever specific laws change in the database, any cache entries relying on those laws are surgically removed without purging the entire cache, maximizing both accuracy and cost-efficiency.

## What Changes
- Enhance the Qdrant Cache payload to store an array of `retrieved_doc_ids` representing the documents retrieved for that query.
- Update the semantic caching layer in the backend to capture and save these IDs upon a Cache Miss.
- Introduce an invalidation mechanism (e.g., to be used by the ingest script) that queries and deletes cache points where `retrieved_doc_ids` matches any modified or deleted document IDs using Qdrant's `MatchAny`.

## Capabilities

### New Capabilities
- `granular-cache-invalidation`: Defines the requirements for selectively invalidating cache entries based on document IDs using Qdrant's MatchAny filter.

### Modified Capabilities
- `semantic-caching`: Modifies the semantic caching capability to include metadata tracking requirements (`retrieved_doc_ids`) during the cache writing phase.

## Impact
- **Backend API (`chat.py`)**: Modifies the cache-saving logic to parse and forward retrieved document IDs.
- **Cache Module (`cache.py`)**: Updates payload structure for the `semantic_cache` collection.
- **Ingest Script**: Adds surgical cache deletion capability when documents are updated or removed.
