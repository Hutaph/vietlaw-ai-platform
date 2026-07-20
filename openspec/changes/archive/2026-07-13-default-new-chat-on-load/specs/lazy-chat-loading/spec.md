## MODIFIED Requirements

### Requirement: Session Metadata Startup
The system SHALL fetch only chat session metadata (id, title, timestamp, message_count) during application startup. The system SHALL NOT fetch messages for any historical session on startup. It MUST always initialize a new empty chat session as the active session.

#### Scenario: User opens the application
- **WHEN** the application mounts and fetches `/api/chat/sessions`
- **THEN** it does NOT automatically fetch messages for any historical session
- **AND** it initializes a new empty chat session as the active session.
