## ADDED Requirements

### Requirement: Cache invalidation by document ID
The system SHALL provide a mechanism to invalidate cache entries based on the document IDs that were originally retrieved for the cached query. This mechanism MUST accept a list of modified or deleted document IDs and purge any cache point whose `retrieved_doc_ids` array contains any of those IDs using Qdrant's `MatchAny` filter.

#### Scenario: Purging outdated cache entries
- **WHEN** the ingest script updates or deletes documents from the main database
- **THEN** it calls the cache invalidation function with the affected document IDs
- **AND** the system successfully deletes all cache points in `semantic_cache` where `retrieved_doc_ids` matches any of the affected IDs
