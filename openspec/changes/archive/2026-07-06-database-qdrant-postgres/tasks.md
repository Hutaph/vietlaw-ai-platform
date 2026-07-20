## 1. Infrastructure Setup

- [x] 1.1 Add Qdrant and PostgreSQL service definitions to docker-compose.yml
- [x] 1.2 Add connection and storage configuration variables to backend configuration
- [x] 1.3 Add Python dependencies for Qdrant and PostgreSQL clients

## 2. Data Model and Schema

- [x] 2.1 Define PostgreSQL schema for laws, clauses, and ingestion state
- [x] 2.2 Define ingestion and indexing metadata models for backend use
- [x] 2.3 Create bootstrap/init scripts for local development

## 3. Ingestion Pipeline

- [x] 3.1 Implement document normalization and clause extraction from processed JSON
- [x] 3.2 Implement PostgreSQL persistence for legal documents and clause records
- [x] 3.3 Implement Qdrant upsert workflow for clause embeddings and metadata
- [x] 3.4 Add support for incremental reindexing and idempotent ingestion

## 4. Retrieval Integration

- [x] 4.1 Introduce a storage abstraction interface for vector and metadata access
- [x] 4.2 Replace the current FAISS-backed retrieval path with the new abstraction
- [x] 4.3 Preserve existing category filtering and context-building behavior
- [x] 4.4 Add fallback behavior for development when database services are unavailable

## 5. Validation and Rollout

- [x] 5.1 Validate end-to-end retrieval with sample legal questions
- [x] 5.2 Update README and local setup instructions for Qdrant/PostgreSQL
- [x] 5.3 Verify docker-compose startup and initial data ingestion flow
