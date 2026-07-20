## ADDED Requirements

### Requirement: Store embeddings in Qdrant
The system MUST store generated clause embeddings in Qdrant with payload data that supports metadata-based filtering.

#### Scenario: Upsert vector payload
- **WHEN** a clause embedding is generated
- **THEN** the system MUST upsert it into Qdrant with a stable identifier and relevant payload fields

#### Scenario: Metadata-aware retrieval support
- **WHEN** a retrieval request includes category or law filters
- **THEN** the system MUST be able to restrict vector search using stored metadata
