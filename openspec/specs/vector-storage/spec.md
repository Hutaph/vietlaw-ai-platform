# Capability: Vector Storage

## Purpose
TBD

## Requirements

### Requirement: Store embeddings in Qdrant
The system MUST store generated clause embeddings in Qdrant with payload data that supports metadata-based filtering, utilizing a Named Vectors schema to store both dense and sparse vectors.

#### Scenario: Upsert vector payload
- **WHEN** a clause embedding is generated
- **THEN** the system MUST upsert it into Qdrant with a stable identifier and relevant payload fields

#### Scenario: Metadata-aware retrieval support
- **WHEN** a retrieval request includes category or law filters
- **THEN** the system MUST be able to restrict vector search using stored metadata

#### Scenario: Upserting named vectors
- **WHEN** a legal clause is vectorized
- **THEN** the system MUST store its dense embedding under the `text-dense` vector name and its sparse embedding under the `text-sparse` vector name
