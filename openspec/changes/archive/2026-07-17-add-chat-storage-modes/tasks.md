## 1. Configuration and runtime contract

- [x] 1.1 Add `CHAT_STORAGE_MODE` with `postgres` and `browser` values and validate invalid values during backend configuration loading.
- [x] 1.2 Add the matching `NEXT_PUBLIC_CHAT_STORAGE_MODE` frontend deployment setting and document that both values must match.
- [x] 1.3 Extend readiness/startup diagnostics with the active chat storage mode and a redacted shared-unauthenticated warning for PostgreSQL mode.
- [x] 1.4 Keep `STORAGE_BACKEND` semantics unchanged for shared legal corpus storage and add configuration regression tests proving both chat modes can use `qdrant_postgres` retrieval.

## 2. Browser-local conversation mode

- [x] 2.1 Update `useChatSessions` to use the existing localStorage snapshot directly in browser mode without calling session list or message APIs.
- [x] 2.2 Make browser-mode session creation, selection, deletion, message updates, and feedback state remain local and refresh-safe.
- [x] 2.3 Ensure the frontend does not silently fall back from browser mode to PostgreSQL when local storage is available or a server request fails.
- [x] 2.4 Add browser-mode UI/runtime handling for the limitations of device-local history and unavailable server analytics.

## 3. Backend persistence and memory gating

- [x] 3.1 Gate non-streaming and streaming chat turn persistence so PostgreSQL writes occur only in `CHAT_STORAGE_MODE=postgres`.
- [x] 3.2 Gate session summary reads, updates, and asynchronous summarization so browser mode never persists conversation memory to PostgreSQL.
- [x] 3.3 Make session list, message retrieval, and delete endpoints return explicit browser-mode responses without reading or deleting shared PostgreSQL data.
- [x] 3.4 Make feedback handling skip PostgreSQL writes in browser mode while preserving current PostgreSQL behavior in shared mode.
- [x] 3.5 Preserve sequential and refresh-safe persistence guarantees for PostgreSQL mode, including semantic-cache hit paths.

## 4. Tests and deployment documentation

- [x] 4.1 Add backend tests for chat storage mode validation, readiness diagnostics, browser-mode persistence suppression, and PostgreSQL-mode compatibility.
- [x] 4.2 Add frontend tests or verification scripts for browser-mode local session restore and the absence of session API calls.
- [x] 4.3 Add regression coverage for memory-summary suppression and feedback behavior in browser mode.
- [x] 4.4 Update `.env.example`, Vercel configuration, README, and deployment documentation with both modes and the shared-data warning.
- [ ] 4.5 Run focused backend/frontend tests, verify legal retrieval remains available in browser mode, and record migration/rollback results.
