## ADDED Requirements

### Requirement: Session Metadata Startup
The system SHALL fetch only chat session metadata (id, title, timestamp) and the messages for the single most recent session during application startup.

#### Scenario: User opens the application
- **WHEN** the application mounts and fetches `/api/chat/sessions`
- **THEN** it does NOT automatically fetch messages for all historical sessions, fetching only messages for the latest active session or creating a new one if none exist.

### Requirement: Lazy Loading Chat Messages
The system SHALL fetch messages for historical sessions on-demand when the user selects them, rather than preemptively.

#### Scenario: User clicks an unloaded session
- **WHEN** the user selects a session in the sidebar whose messages have not yet been loaded
- **THEN** the system sets a loading state and makes a single API request to `/api/chat/session/[id]/messages`.

#### Scenario: User clicks an already loaded session
- **WHEN** the user selects a session in the sidebar whose messages were previously loaded in this browser session
- **THEN** the system instantly displays the cached messages without making a redundant API request.

### Requirement: Chat Skeleton Loader
The system SHALL display a skeleton loading UI in the main chat interface while a newly selected session's messages are being fetched from the server.

#### Scenario: Session messages are loading
- **WHEN** the `isSessionLoading` state is active
- **THEN** the main chat window displays placeholder visual elements (skeletons) representing generic user and assistant message bubbles.
