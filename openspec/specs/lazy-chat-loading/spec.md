## Purpose

Keep initial chat loading fast while preserving the active conversation across refreshes. Historical messages should load lazily, and browser-cached messages should be reconciled with PostgreSQL when the backend has a more complete message list.

## Requirements

### Requirement: Session Metadata Startup
The system SHALL fetch only chat session metadata (id, title, timestamp, message_count) during application startup. The system SHALL NOT fetch messages for every historical session on startup. If there is no active session recorded in browser storage, it MUST initialize a new empty chat state without immediately rendering a placeholder session in the historical list. The new session SHALL only be persisted to the sidebar list once a message is generated.

#### Scenario: User opens the application
- **WHEN** the application mounts and fetches `/api/chat/sessions`
- **AND** no active session id is available in browser storage
- **THEN** it does NOT fetch messages for any historical session
- **AND** it sets the active session to a new empty state, leaving the historical list exactly as returned by the server.

### Requirement: Active Session Restore
The system SHALL preserve the active session id in browser storage so a page refresh can return to the conversation the user was viewing. Restoring an active session MUST NOT merge messages into a different session.

#### Scenario: User refreshes while viewing an existing session
- **WHEN** the application mounts and the stored active session id exists in `/api/chat/sessions`
- **THEN** it sets that id as the current active session
- **AND** follow-up messages are sent with that same `sessionId`.

#### Scenario: Active session exists only in local cache during backend catch-up
- **WHEN** the application mounts and the stored active session id is missing from `/api/chat/sessions`
- **AND** local cached messages exist for that id
- **THEN** the system keeps that session in the sidebar and restores it as active
- **AND** it does NOT fall back to another historical session.

### Requirement: Lazy Loading Chat Messages
The system SHALL fetch messages for historical sessions on-demand when the user selects them, rather than preemptively loading all sessions.

#### Scenario: User clicks an unloaded session
- **WHEN** the user selects a session in the sidebar whose messages have not yet been loaded
- **THEN** the system sets a loading state and makes a single API request to `/api/chat/session/[id]/messages`.

#### Scenario: User clicks an already loaded session
- **WHEN** the user selects a session in the sidebar whose messages were previously loaded in this browser session
- **THEN** the system instantly displays the cached messages
- **AND** it may fetch `/api/chat/session/[id]/messages` in the background to reconcile with PostgreSQL.

### Requirement: Message Cache Reconciliation
The frontend SHALL prefer PostgreSQL session messages when the backend reports more messages than the local browser cache. This prevents refreshes from showing only the user question when the assistant response has already reached PostgreSQL.

#### Scenario: Active session cache is stale
- **WHEN** the app restores an active session from browser storage
- **AND** `/api/chat/sessions` reports a `message_count` greater than the locally cached message count
- **THEN** the frontend fetches `/api/chat/session/[id]/messages`
- **AND** updates the restored session with the more complete PostgreSQL message list.

### Requirement: Chat Skeleton Loader
The system SHALL display a skeleton loading UI in the main chat interface while a newly selected session's messages are being fetched from the server.

#### Scenario: Session messages are loading
- **WHEN** the `isSessionLoading` state is active
- **THEN** the main chat window displays placeholder visual elements (skeletons) representing generic user and assistant message bubbles.

### Requirement: Session list includes message count
API `GET /chat/sessions` SHALL trả về danh sách sessions trong đó mỗi session object PHẢI bao gồm trường `message_count` kiểu integer biểu thị số lượng messages thuộc session đó. Trường này PHẢI được tính toán server-side thông qua SQL COUNT, không phải client-side.

#### Scenario: Sessions returned with message count
- **WHEN** client gọi `GET /chat/sessions`
- **THEN** mỗi object trong mảng kết quả có trường `message_count` kiểu số nguyên không âm

#### Scenario: Empty session has zero message count
- **WHEN** session tồn tại trong `chat_sessions` nhưng không có rows nào trong `chat_messages`
- **THEN** `message_count` = 0 cho session đó

#### Scenario: Frontend filters empty sessions from sidebar
- **WHEN** `useChatSessions` nhận danh sách sessions từ API
- **THEN** chỉ những session có `message_count > 0` HOẶC là `currentSessionId` hiện tại mới được hiển thị trong sidebar
