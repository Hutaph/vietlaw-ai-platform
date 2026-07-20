# Capability: Document Ingestion

## Purpose
TBD

## Requirements

### Requirement: Ingest legal documents into persistent storage
The system MUST ingest processed legal JSON documents into a persistent storage pipeline that stores law metadata and clause data in PostgreSQL, and generates both dense and sparse vectors for Qdrant storage.

#### Scenario: Successful ingestion from processed JSON
- **WHEN** a processed legal JSON document is available
- **THEN** the system MUST normalize the document into law and clause records, generate dense and sparse vectors, and persist them into PostgreSQL and Qdrant

#### Scenario: Idempotent ingestion
- **WHEN** the same document is ingested more than once
- **THEN** the system MUST avoid duplicate records and update existing records deterministically

### Requirement: Track ingestion state
The system MUST record ingestion status for each processing run so that reindex and retry workflows can be monitored.

#### Scenario: Recording ingestion run
- **WHEN** an ingestion run starts or completes
- **THEN** the system MUST create or update an indexing run record with status and metadata
