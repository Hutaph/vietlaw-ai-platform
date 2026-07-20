## Purpose

Ensure chat sessions and their related messages are persisted to PostgreSQL in a sequential, consistent, and refresh-safe way. Each completed turn must contain both the user message and the assistant response before the client treats the turn as complete.

## Requirements

### Requirement: Sequential turn persistence
When `CHAT_STORAGE_MODE=postgres`, the system SHALL persist each chat turn to PostgreSQL in this order: `ensure_session_exists` -> `save_chat_message(user)` -> `save_chat_message(assistant)`. The system MUST NOT dispatch those three operations as independent parallel tasks. When `CHAT_STORAGE_MODE=browser`, the backend MUST skip all three operations.

#### Scenario: Successful turn persist on stream endpoint
- **WHEN** streaming completes and `accumulated_text` is non-empty in PostgreSQL mode
- **THEN** `chat_sessions` contains a row for the corresponding `session_id`
- **AND** `chat_messages` contains exactly the user and assistant rows for that turn
- **AND** the rows are ordered by `created_at`
- **AND** both rows have non-empty `content`.

#### Scenario: Successful turn persist on non-stream endpoint
- **WHEN** `/chat` returns a successful response in PostgreSQL mode
- **THEN** `chat_messages` contains the user/assistant pair for that turn
- **AND** the user message content matches the latest user message from the request.

#### Scenario: Successful turn persist on cache hit path
- **WHEN** semantic cache serves a response through `/chat` or `/chat/stream` in PostgreSQL mode
- **THEN** the user/assistant pair is still persisted to `chat_messages`.

#### Scenario: Browser mode skips server persistence
- **WHEN** a chat turn completes with `CHAT_STORAGE_MODE=browser`
- **THEN** the backend does not call `ensure_session_exists`, `save_chat_message`, or any PostgreSQL conversation write

#### Scenario: FK constraint never violated
- **WHEN** `save_chat_message` is called in PostgreSQL mode
- **THEN** the corresponding `chat_sessions` row already exists
- **AND** no foreign key violation is logged.

### Requirement: Refresh-safe turn completion
The chat API SHALL persist the complete user/assistant turn before the client is allowed to treat the turn as finished when `CHAT_STORAGE_MODE=postgres`. For non-streaming `/chat`, the response MUST NOT be returned until the turn has been written. For streaming `/chat/stream`, the final `done` SSE event MUST NOT be emitted until the turn has been written. In browser mode, completion MUST depend only on successful inference and local frontend persistence.

#### Scenario: User refreshes immediately after streaming completes
- **WHEN** `/chat/stream` emits the final `done` event in PostgreSQL mode
- **THEN** PostgreSQL already contains both the user message and assistant message for that turn
- **AND** reloading `/chat/session/{session_id}/messages` returns the complete turn.

#### Scenario: User refreshes immediately after non-streaming response
- **WHEN** `/chat` returns a successful JSON response in PostgreSQL mode
- **THEN** PostgreSQL already contains both the user message and assistant message for that turn.

#### Scenario: Browser mode refreshes after completion
- **WHEN** the browser is refreshed after a successful chat turn in browser mode
- **THEN** the frontend restores the completed turn from browser-local storage without requiring PostgreSQL

#### Scenario: Semantic cache hit returns an answer
- **WHEN** either `/chat` or `/chat/stream` serves a response from semantic cache in PostgreSQL mode
- **THEN** the cached response is persisted as the assistant message before the client receives completion.
