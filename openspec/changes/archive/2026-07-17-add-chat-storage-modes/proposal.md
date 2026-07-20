## Why

The deployed application currently persists chat sessions, messages, summaries, and feedback to a shared PostgreSQL database without user authentication. This causes users to share the same conversation history and creates an avoidable privacy boundary problem, while the legal knowledge base still needs shared PostgreSQL/Qdrant storage for retrieval.

## What Changes

- Add an explicit chat storage mode with `postgres` and `browser` options.
- Keep legal corpus storage controlled independently by `STORAGE_BACKEND`.
- Make `browser` mode use the existing browser-local session storage as the source of truth and prevent chat/session/feedback persistence to PostgreSQL.
- Preserve `postgres` mode for shared/demo deployments and expose its unauthenticated shared-data behavior clearly.
- Make frontend session loading and persistence mode-aware instead of probing PostgreSQL and falling back silently.
- Make backend session persistence, memory summaries, session APIs, and feedback handling honor the selected chat storage mode.
- Define browser-mode behavior for server-side conversation memory and analytics.
- Add configuration, readiness diagnostics, regression tests, and deployment documentation for both modes.

## Capabilities

### New Capabilities

- `chat-storage-modes`: Select and enforce browser-local or PostgreSQL-backed storage for user conversation data independently from the shared legal knowledge base.

### Modified Capabilities

- `sequential-chat-persistence`: Make sequential PostgreSQL turn persistence conditional on the selected chat storage mode.
- `memory-manager`: Define how conversation summaries and memory behave when browser-local storage is selected.

## Impact

- Backend configuration and readiness reporting.
- Chat completion and streaming persistence paths.
- Session listing, message retrieval, deletion, and feedback APIs.
- Frontend `useChatSessions` loading/saving behavior and runtime storage-mode configuration.
- PostgreSQL chat tables remain available for shared mode, while browser mode avoids writes to those tables.
- PostgreSQL/Qdrant legal corpus retrieval remains shared and unchanged.
- Deployment environment variables and documentation.
