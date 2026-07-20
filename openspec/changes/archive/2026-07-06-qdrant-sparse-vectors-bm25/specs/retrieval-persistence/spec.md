## MODIFIED Requirements

### Requirement: Retrieve legal context from persistent storage
The system MUST support legal retrieval through the new persistent storage layer utilizing Qdrant's native Hybrid Search (RRF) mechanism across both dense and sparse vectors.

#### Scenario: Successful hybrid retrieval
- **WHEN** a user submits a legal question through the existing chat endpoint
- **THEN** the system MUST execute a `query_points` request with dual prefetch (dense and sparse) and return RRF-fused context to the LLM pipeline

#### Scenario: Fallback behavior
- **WHEN** the persistent storage services are unavailable
- **THEN** the system MUST fall back gracefully to the existing local behavior rather than failing the request completely
