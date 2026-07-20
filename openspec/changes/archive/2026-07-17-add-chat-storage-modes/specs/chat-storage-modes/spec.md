## ADDED Requirements

### Requirement: Explicit chat storage mode

The system SHALL support an explicit `CHAT_STORAGE_MODE` configuration with the values `postgres` and `browser`, independently from the `STORAGE_BACKEND` used for the shared legal corpus.

#### Scenario: Browser mode is selected

- **WHEN** the backend starts with `CHAT_STORAGE_MODE=browser`
- **THEN** conversation persistence uses browser-local storage at the frontend boundary and the backend does not persist chat sessions, messages, summaries, or feedback to PostgreSQL

#### Scenario: PostgreSQL mode is selected

- **WHEN** the backend starts with `CHAT_STORAGE_MODE=postgres`
- **THEN** the existing PostgreSQL-backed session, message, summary, and feedback behavior remains available

#### Scenario: Invalid chat storage mode

- **WHEN** `CHAT_STORAGE_MODE` is set to a value other than `postgres` or `browser`
- **THEN** startup or readiness fails with a clear configuration error that identifies the invalid setting

### Requirement: Legal corpus storage remains independent

The system SHALL continue to use the configured `STORAGE_BACKEND` for the shared legal corpus and retrieval services regardless of the selected chat storage mode.

#### Scenario: Browser mode uses shared legal retrieval

- **WHEN** `CHAT_STORAGE_MODE=browser` and `STORAGE_BACKEND=qdrant_postgres`
- **THEN** legal documents remain available through PostgreSQL/Qdrant retrieval while user conversation data remains browser-local

#### Scenario: Chat mode does not disable corpus initialization

- **WHEN** the application starts in either chat storage mode with a database-backed legal storage configuration
- **THEN** laws, clauses, indexing metadata, and Qdrant collection checks follow the existing storage configuration

### Requirement: Browser-local session source of truth

The frontend SHALL use its existing browser-local session snapshot as the source of truth in browser mode and SHALL NOT probe PostgreSQL session APIs before restoring local sessions.

#### Scenario: Browser mode loads sessions

- **WHEN** the chat UI mounts with `NEXT_PUBLIC_CHAT_STORAGE_MODE=browser`
- **THEN** it restores sessions, messages, active session state, and feedback from browser storage without requesting `/chat/sessions` or `/chat/session/{id}/messages`

#### Scenario: Browser mode persists a turn

- **WHEN** a user completes a chat turn in browser mode
- **THEN** the frontend updates its local session snapshot and the backend does not create or update PostgreSQL chat rows

#### Scenario: Browser mode deletes a session

- **WHEN** a user deletes a session in browser mode
- **THEN** the frontend removes the local session and messages without sending a PostgreSQL delete request

### Requirement: Shared PostgreSQL mode warning

The system SHALL identify PostgreSQL chat storage as shared and unauthenticated when no user ownership mechanism is configured.

#### Scenario: Readiness reports shared storage

- **WHEN** readiness is checked with `CHAT_STORAGE_MODE=postgres` and authentication is not configured
- **THEN** the response includes a non-secret warning that chat sessions and feedback are shared across users

#### Scenario: Browser mode reports local privacy boundary

- **WHEN** readiness is checked with `CHAT_STORAGE_MODE=browser`
- **THEN** the response identifies conversation storage as browser-local and does not report PostgreSQL chat persistence as active

### Requirement: Mode-aware conversation and feedback APIs

The backend SHALL enforce the selected chat storage mode at conversation and feedback API boundaries rather than relying only on frontend behavior.

#### Scenario: Browser mode receives a session list request

- **WHEN** `/chat/sessions` is called while `CHAT_STORAGE_MODE=browser`
- **THEN** the backend returns an explicit storage-mode response without listing PostgreSQL sessions

#### Scenario: Browser mode receives a message or delete request

- **WHEN** a session message or delete endpoint is called while `CHAT_STORAGE_MODE=browser`
- **THEN** the backend does not read or delete PostgreSQL conversation data and returns an explicit storage-mode response

#### Scenario: Browser mode receives feedback

- **WHEN** feedback is submitted while `CHAT_STORAGE_MODE=browser`
- **THEN** the backend skips PostgreSQL feedback persistence and returns a non-error response indicating that feedback was not persisted server-side

#### Scenario: PostgreSQL mode receives a conversation request

- **WHEN** a conversation or feedback endpoint is called while `CHAT_STORAGE_MODE=postgres`
- **THEN** the endpoint uses the existing PostgreSQL implementation and preserves its current error handling
