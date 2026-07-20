## MODIFIED Requirements

### Requirement: Session Summary Storage

The system SHALL store and update a summary of the conversation context for a given `session_id` only when `CHAT_STORAGE_MODE=postgres`. In browser mode, the backend MUST NOT read or write a PostgreSQL session summary.

#### Scenario: New session
- **WHEN** a chat interaction occurs for a new `session_id` in PostgreSQL mode
- **THEN** a new chat session record is implicitly tracked or created with an empty summary

#### Scenario: Updating summary
- **WHEN** a background task finishes generating a new summary for a session in PostgreSQL mode
- **THEN** the system updates the `summary` and `turn_count` tracking for that session in the storage backend

#### Scenario: Browser mode has no server summary
- **WHEN** a chat interaction occurs in browser mode
- **THEN** the backend skips session-summary reads and writes and does not create a PostgreSQL chat session

### Requirement: Sliding Window Context Construction

The system SHALL combine the stored session summary with a sliding window of the most recent messages in PostgreSQL mode. In browser mode, it SHALL construct context from the request's client-provided message history without fetching a server-side summary.

#### Scenario: Summarized context injection
- **WHEN** the chat endpoint receives a prompt request for a session with multiple previous turns in PostgreSQL mode
- **THEN** it retrieves the summary from the database and prefixes the chat history string with the summary, followed by the verbatim last N messages

#### Scenario: Browser-local context construction
- **WHEN** the chat endpoint receives a prompt request in browser mode
- **THEN** it does not query PostgreSQL for a summary and uses the request's recent messages for the configured context window

### Requirement: Asynchronous Summarizer Task

The system SHALL automatically summarize past conversation history asynchronously without blocking the user response only when `CHAT_STORAGE_MODE=postgres`. When a runtime summarizer provider/model is configured in the chat request, the summarizer SHALL use that runtime role configuration for the background summarization task. In browser mode, the backend MUST skip the summarizer task because no server-side summary is persisted.

#### Scenario: Triggering summarization
- **WHEN** the streaming generation finishes or a non-streaming endpoint completes with memory enabled in PostgreSQL mode
- **THEN** an async background task is launched to invoke a lightweight LLM to summarize the newly appended messages into the existing summary

#### Scenario: Runtime summarizer role is configured
- **WHEN** a chat request includes a valid runtime provider/model for the summarizer role and memory is enabled in PostgreSQL mode
- **THEN** the background summarizer uses the configured summarizer role model for that request.

#### Scenario: Browser mode skips summarization
- **WHEN** a chat request completes in browser mode with memory enabled
- **THEN** the backend does not launch a PostgreSQL-backed summary update task

#### Scenario: Summarizer role is unavailable
- **WHEN** memory is enabled but no summarizer role can be created from runtime or server fallback configuration in PostgreSQL mode
- **THEN** the system logs a non-secret warning and skips summary update without failing the user response.
