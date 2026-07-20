## ADDED Requirements

### Requirement: Session Summary Storage
The system SHALL store and update a summary of the conversation context for a given `session_id`.

#### Scenario: New session
- **WHEN** a chat interaction occurs for a new session_id
- **THEN** a new chat session record is implicitly tracked or created with an empty summary

#### Scenario: Updating summary
- **WHEN** a background task finishes generating a new summary for a session
- **THEN** the system updates the `summary` and `turn_count` tracking for that session in the storage backend

### Requirement: Sliding Window Context Construction
The system SHALL combine the stored session summary with a sliding window of the most recent messages to form the prompt.

#### Scenario: Summarized context injection
- **WHEN** the chat endpoint receives a prompt request for a session with multiple previous turns
- **THEN** it retrieves the summary from the database and prefixes the chat history string with the summary, followed by the verbatim last N messages

### Requirement: Asynchronous Summarizer Task
The system SHALL automatically summarize past conversation history asynchronously without blocking the user response.

#### Scenario: Triggering summarization
- **WHEN** the streaming generation finishes or a non-streaming endpoint completes
- **THEN** an async background task is launched to invoke a lightweight LLM to summarize the newly appended messages into the existing summary
