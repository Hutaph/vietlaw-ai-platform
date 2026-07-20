## ADDED Requirements

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

### Requirement: Document Conversational Memory Manager
The `project-context.md` file MUST document the background task that incrementally summarizes chat history.

#### Scenario: Understanding chat context
- **WHEN** reviewing the backend flow
- **THEN** the memory manager's role in summarizing and persisting history is explained.
