## Context

The current retrieval stack relies on local JSON documents plus a FAISS index stored on disk. This works for a demo environment but makes ingestion, updates, and scaling cumbersome. The proposed migration replaces the local vector store with Qdrant and introduces PostgreSQL for relational metadata and indexing state.

The backend already uses a modular pipeline, so the migration can be introduced as an internal storage abstraction rather than a full rewrite of the chat experience. The frontend contract remains unchanged, and the main change is in how documents are ingested and retrieved.

## Goals / Non-Goals

**Goals:**
- Introduce a persistent, service-backed storage layer for legal clause embeddings.
- Add PostgreSQL-backed persistence for legal metadata and ingestion state.
- Preserve the existing chat API and retrieval behavior at the application level.
- Make future incremental indexing and document updates feasible.

**Non-Goals:**
- Reworking the frontend experience or chat UX.
- Replacing the RAG prompt strategy or LLM integration.
- Building full admin UI for document management.

## Decisions

1. Use Qdrant for vector storage and retrieval.
   - Rationale: Qdrant provides filterable vector search, better operational support for metadata-aware retrieval, and a cleaner path to scale than a local FAISS index.
   - Alternatives considered: keep FAISS and add a wrapper around a remote store, or use a different vector DB. Qdrant was selected because it fits the current retrieval model and supports metadata filtering directly.

2. Use PostgreSQL for relational metadata and ingestion state.
   - Rationale: PostgreSQL is well suited for storing law metadata, clause attributes, ingestion status, and future audit/history fields.
   - Alternatives considered: SQLite or JSON-only storage. PostgreSQL was selected for stronger production readiness and easier multi-service operation.

3. Introduce a storage abstraction layer in the backend.
   - Rationale: the existing pipeline already has clear separation between retrieval, reranking, and context building. The storage layer should be hidden behind a common interface so searcher and ingestion code do not depend on the underlying implementation.
   - Alternatives considered: patching the existing FAISS modules in place. The abstraction approach is cleaner and reduces coupling.

4. Keep the public chat API unchanged for now.
   - Rationale: the migration should be transparent to the frontend while the retrieval internals evolve.
   - Alternatives considered: changing API payloads to expose storage details or ingestion status. That would be premature for the initial rollout.

5. Use an ingestion pipeline that writes to PostgreSQL first and vector store second.
   - Rationale: this ensures relational metadata is authoritative and that vector upserts are derived from a validated document record.
   - Alternatives considered: write directly to Qdrant and reconstruct metadata later. The PostgreSQL-first path is more robust and supports future features.

## Risks / Trade-offs

- [Data consistency between PostgreSQL and Qdrant] → Mitigation: use a single ingestion workflow with transactional metadata writes and deterministic upsert IDs.
- [Migration complexity for existing local index files] → Mitigation: support a fallback mode that loads from local files during transition and gradually backfills into the new services.
- [Embedding cost and latency] → Mitigation: batch ingestion, reuse embeddings where possible, and support incremental reindexing.
- [Operational complexity] → Mitigation: provide Docker Compose services and a bootstrap script for local development.

## Migration Plan

1. Add Qdrant and PostgreSQL services to the local development stack.
2. Introduce backend configuration for connection strings and storage mode selection.
3. Implement database schema and ingestion scripts for legal documents and clauses.
4. Build the new storage abstraction and swap the retrieval pipeline to use it.
5. Validate retrieval quality against the current FAISS-based behavior and keep fallback support during rollout.

## Open Questions

- Should the initial rollout support full reindex from existing JSON files, or only newly ingested documents?
- What document versioning model should be used for legal updates over time?
- Should the system expose indexing status through a lightweight admin or debug endpoint?
