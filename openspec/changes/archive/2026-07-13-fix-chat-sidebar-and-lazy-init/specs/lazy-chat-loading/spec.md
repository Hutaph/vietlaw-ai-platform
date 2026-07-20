## MODIFIED Requirements

### Requirement: Session Metadata Startup
The system SHALL fetch only chat session metadata (id, title, timestamp, message_count) during application startup. The system SHALL NOT fetch messages for any historical session on startup. It MUST initialize a new empty chat state without immediately rendering a placeholder session in the historical list. The new session SHALL only be persisted to the sidebar list once a message is generated.

#### Scenario: User opens the application
- **WHEN** the application mounts and fetches `/api/chat/sessions`
- **THEN** it does NOT automatically fetch messages for any historical session
- **AND** it sets the active session to a new empty state, leaving the historical list exactly as returned by the server.
