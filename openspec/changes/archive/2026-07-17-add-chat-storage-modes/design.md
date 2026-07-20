## Context

The deployed application uses PostgreSQL and Qdrant for the shared legal corpus, while the frontend already mirrors chat sessions and messages in `localStorage`. The backend currently persists chat sessions, messages, memory summaries, and feedback whenever `STORAGE_BACKEND` is database-backed. Because the deployment has no authentication, that behavior makes all users share the same conversation tables and exposes cross-user history through session APIs.

The change must preserve shared PostgreSQL/Qdrant retrieval while adding an explicit choice for user-generated conversation data. The current frontend/backend fallback behavior must not silently turn a browser-local deployment into a shared database deployment.

## Goals / Non-Goals

**Goals:**

- Add explicit `CHAT_STORAGE_MODE=postgres|browser` configuration.
- Keep legal corpus storage independent from chat storage.
- Make browser mode use the existing browser-local session snapshot as the source of truth.
- Prevent browser mode from writing or reading chat sessions, messages, summaries, or feedback from PostgreSQL.
- Preserve the current sequential PostgreSQL persistence guarantees in postgres mode.
- Make memory, feedback, session APIs, readiness diagnostics, and frontend session loading mode-aware.
- Warn clearly that postgres mode is shared and unauthenticated.

**Non-Goals:**

- Adding authentication, authorization, user accounts, or PostgreSQL row ownership.
- Changing the shared legal corpus schema or Qdrant retrieval behavior.
- Encrypting `localStorage` or providing cross-device browser synchronization.
- Replacing `localStorage` with IndexedDB in this change.

## Decisions

### 1. Separate chat storage from legal corpus storage

Introduce `CHAT_STORAGE_MODE` instead of overloading `STORAGE_BACKEND`. `STORAGE_BACKEND=qdrant_postgres` remains valid in both modes because PostgreSQL/Qdrant still hold the shared laws, clauses, indexing metadata, and retrieval vectors.

The accepted values are:

- `postgres`: persist chat sessions, messages, summaries, and feedback in PostgreSQL.
- `browser`: keep user conversation state in browser storage and keep the backend stateless for conversation persistence.

The default deployment recommendation is `browser`; `postgres` is retained for trusted demos and deployments that explicitly accept shared unauthenticated data.

### 2. Keep frontend and backend mode configuration aligned

The backend reads `CHAT_STORAGE_MODE` for enforcement and readiness. The client-side session hook reads a corresponding `NEXT_PUBLIC_CHAT_STORAGE_MODE` value so it can avoid making PostgreSQL session requests in browser mode. Deployment documentation will require both values to match, and startup/readiness diagnostics will expose the backend mode without secrets.

An eventual runtime configuration endpoint may remove the duplicated frontend variable, but it is outside this change.

### 3. Browser mode fails closed for server persistence

When browser mode is active, chat completion and streaming endpoints MUST skip session/message persistence and MUST NOT call the PostgreSQL memory summary functions. Session list/message/delete APIs return an explicit storage-mode response rather than exposing shared database data. Feedback persistence is skipped; the frontend keeps the feedback state in its existing local snapshot.

The frontend will not use "database unavailable" fallback as the mode switch. It will choose local storage before making session API calls.

### 4. Define browser-mode memory behavior explicitly

Server-side summary memory is a PostgreSQL feature in this release. Browser mode disables server summary reads and asynchronous summary writes. The request's existing message history remains available to the chat pipeline, so the browser mode continues to support the configured recent-message context without creating server-side conversation records.

### 5. Preserve shared-mode compatibility and warn about privacy

Postgres mode keeps the current sequential order `ensure_session_exists -> user message -> assistant message` and refresh-safe completion guarantees. Readiness and deployment documentation report that the mode is shared/unauthenticated so operators do not mistake it for per-user isolation.

### 6. Prefer existing browser storage over a new client database

The frontend already stores sessions, messages, active session state, and message feedback in `localStorage`. Reusing that snapshot minimizes migration and dependency risk. Its limitations—device-local data, browser clearing, quota limits, and lack of encryption—will be documented.

## Risks / Trade-offs

- **[Shared data exposure in postgres mode]** → Label the mode as shared/unauthenticated in readiness and documentation; recommend browser mode until authentication exists.
- **[Frontend/backend configuration drift]** → Require matching `CHAT_STORAGE_MODE` and `NEXT_PUBLIC_CHAT_STORAGE_MODE`, add validation/tests, and expose the backend mode in readiness diagnostics.
- **[Users lose cross-device history in browser mode]** → Document that browser mode is device/browser-profile local and intentionally does not synchronize.
- **[localStorage is not secure storage]** → Document that it is not encryption or XSS protection; avoid storing provider secrets as part of this change.
- **[Memory quality differs by mode]** → Disable server summary memory in browser mode and keep the behavior explicit rather than silently writing shared summaries.
- **[Existing database records remain after switching to browser mode]** → Do not delete or migrate existing PostgreSQL data automatically; switching mode only changes future access and writes.

## Migration Plan

1. Deploy with `CHAT_STORAGE_MODE=browser` and `NEXT_PUBLIC_CHAT_STORAGE_MODE=browser` for privacy-preserving shared deployments.
2. Keep `STORAGE_BACKEND=qdrant_postgres` and existing Qdrant/PostgreSQL corpus settings unchanged.
3. Verify that chat works, browser refresh restores local sessions, no chat rows are added to PostgreSQL, and legal retrieval still works.
4. To return to shared persistence, set both mode variables to `postgres` and redeploy. Existing PostgreSQL history becomes visible again through the shared session APIs.
5. Roll back the code/configuration together if the mode contract is invalid; do not silently fall back from browser mode to PostgreSQL.

## Open Questions

- Should browser-mode feedback remain only in `localStorage`, or should the product disable the feedback action entirely when analytics persistence is unavailable?
- Should a future authenticated mode use the same `postgres` value with ownership enforcement, or introduce a separate `postgres_user_scoped` mode?
