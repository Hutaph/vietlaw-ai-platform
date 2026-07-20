## MODIFIED Requirements

### Requirement: Retrieve legal context from persistent storage
The system MUST support legal retrieval through the new persistent storage layer utilizing Qdrant's native Hybrid Search (RRF) mechanism across both dense and sparse vectors, supporting multi-query execution.

#### Scenario: Successful hybrid retrieval with multiple queries
- **WHEN** the query rewriter outputs an array of search queries
- **THEN** the system MUST execute a `query_points` request with dual prefetch for each query, pool the results, remove duplicates, and pass the unique documents to the reranker

#### Scenario: Bypassing retrieval for chitchat
- **WHEN** the query rewriter classifies the input as "chitchat"
- **THEN** the system MUST skip Qdrant retrieval entirely and return an empty context

#### Scenario: Fallback behavior
- **WHEN** the persistent storage services are unavailable
- **THEN** the system MUST fall back gracefully to the existing local behavior rather than failing the request completely
