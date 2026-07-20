# Capability: Retrieval Persistence

## Purpose
This capability defines persistent hybrid legal retrieval, multi-query orchestration, and resilient fallback behavior.

## Requirements

### Requirement: Retrieve legal context from persistent storage
The system MUST support legal retrieval through the new persistent storage layer utilizing Qdrant's native Hybrid Search (RRF) mechanism across both dense and sparse vectors, supporting multi-query execution.

#### Scenario: Successful hybrid retrieval with multiple queries
- **WHEN** the query rewriter outputs an array of search queries
- **THEN** the system MUST execute a `query_points` request with dual prefetch for each query, pool the results, remove duplicates, and pass the unique documents to the reranker

#### Scenario: Async retrieval is not duplicated
- **WHEN** an async chat request invokes persistent retrieval for one or more rewritten queries
- **THEN** each rewritten query is embedded and searched once, and the pipeline does not repeat the same `asearch()` or synchronous fallback dispatch for capability detection

#### Scenario: Bypassing retrieval for chitchat
- **WHEN** the query rewriter classifies the input as "chitchat"
- **THEN** the system MUST skip Qdrant retrieval entirely and return an empty context

#### Scenario: Fallback behavior
- **WHEN** the persistent storage services are unavailable
- **THEN** the system MUST fall back gracefully to the existing local behavior rather than failing the request completely
