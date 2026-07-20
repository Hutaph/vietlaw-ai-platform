## MODIFIED Requirements

### Requirement: Asynchronous Summarizer Task
The system SHALL automatically summarize past conversation history asynchronously without blocking the user response. When a runtime summarizer provider/model is configured in the chat request, the summarizer SHALL use that runtime role configuration for the background summarization task.

#### Scenario: Triggering summarization
- **WHEN** the streaming generation finishes or a non-streaming endpoint completes
- **THEN** an async background task is launched to invoke a lightweight LLM to summarize the newly appended messages into the existing summary

#### Scenario: Runtime summarizer role is configured
- **WHEN** a chat request includes a valid runtime provider/model for the summarizer role and memory is enabled
- **THEN** the background summarizer uses the configured summarizer role model for that request.

#### Scenario: Summarizer role is unavailable
- **WHEN** memory is enabled but no summarizer role can be created from runtime or server fallback configuration
- **THEN** the system logs a non-secret warning and skips summary update without failing the user response.
