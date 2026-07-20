## Why

The core architecture document `openspec/specs/project-context.md` is severely outdated and contradicts the current codebase. It claims that no relational database is used and chat sessions are stored only locally in the browser, whereas the actual implementation relies heavily on PostgreSQL for storing legal content, chat sessions, chat messages, and memory summaries, as well as Qdrant for semantic caching and hybrid search. We need to synchronize the documentation with the source code to avoid confusion and maintain an accurate single source of truth.

## What Changes

- Update `openspec/specs/project-context.md` to accurately reflect the data storage model (PostgreSQL + Qdrant).
- Update the documentation on API conventions to include the new backend session endpoints (`GET /chat/sessions`, `GET /chat/session/{session_id}/messages`, `DELETE /chat/session/{session_id}`).
- Document the new "Conversational Memory Manager" background summarization workflow that uses a lightweight LLM to compress chat histories and persist them in PostgreSQL.
- Document the Semantic Cache system that uses Qdrant to cache queries and reduce latency.
- Update frontend proxy API documentation to reflect that session data is synced with the backend.

## Capabilities

### New Capabilities

*(No new product capabilities are being introduced; this is a documentation synchronization effort).*

### Modified Capabilities

- `project-context`: The project context documentation needs to be updated to reflect the new architecture, specifically the use of PostgreSQL for storage, new API routes for sessions, semantic caching, and the conversational memory manager.

## Impact

- **Documentation**: Updates `openspec/specs/project-context.md`.
- **System**: No changes to application source code. This change purely updates architectural documentation to reflect reality.
