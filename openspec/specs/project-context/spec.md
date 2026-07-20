# Project Context Specifications

## Purpose
TBD: This spec outlines the core architectural and contextual requirements of the project. (Refer to `project-context.md` for full architectural details).

## Requirements

### Requirement: Document Database Storage
The `project-context.md` file MUST document that the system uses PostgreSQL for relational data (laws, clauses, sessions, messages) and Qdrant for vector storage.

#### Scenario: Reading the data model section
- **WHEN** a developer or AI reads the data model section
- **THEN** they see PostgreSQL and Qdrant listed as the primary databases, not just JSON files.

### Requirement: Document Session Synchronization
The `project-context.md` file MUST document that chat sessions and messages are persisted to the backend PostgreSQL database via API routes.

#### Scenario: Reading the UI conventions
- **WHEN** reading the product behavior section
- **THEN** it is stated that sessions are synced with the backend rather than being purely local.

### Requirement: Document Refresh-Safe Chat Sessions
The `project-context.md` file MUST document that the frontend restores the active session on refresh and reconciles browser-cached messages with PostgreSQL when the backend has a larger message count.

#### Scenario: Reading chat session behavior
- **WHEN** reading the data model or UI behavior sections
- **THEN** it is stated that the active session id is restored from browser storage
- **AND** PostgreSQL remains authoritative for complete historical messages.

### Requirement: Document Completion Persistence Boundary
The `project-context.md` file MUST document that completed chat turns are persisted before `/chat` returns or `/chat/stream` emits `done`.

#### Scenario: Understanding refresh consistency
- **WHEN** reviewing the backend flow
- **THEN** it is clear that chat message persistence is completion-blocking
- **AND** only memory summarization remains asynchronous after the turn.

### Requirement: Document Conversational Memory Manager
The `project-context.md` file MUST document the background task that incrementally summarizes chat history.

#### Scenario: Understanding chat context
- **WHEN** reviewing the backend flow
- **THEN** the memory manager's role in summarizing and persisting history is explained.
