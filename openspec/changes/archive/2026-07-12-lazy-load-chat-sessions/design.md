## Context

The `useChatSessions` hook is currently fetching messages for ALL chat sessions using `Promise.all` immediately upon component mount. When users accumulate a large history (e.g., 50+ sessions), this behavior fires dozens of simultaneous HTTP requests, severely impacting application load time, database load, and risk of hitting Vercel serverless rate limits. A more sustainable architecture requires lazy-loading messages only when a session is active.

## Goals / Non-Goals

**Goals:**
- Optimize application startup time by fetching only a lightweight list of sessions without their messages.
- Fetch messages only for the currently selected active session.
- Add an `isSessionLoading` state to manage the visual transition when switching to a session that hasn't been fetched yet.
- Cache fetched messages so subsequent selections of the same session are instantaneous.
- Implement a Skeleton Loader UI in `ChatInterface` for the loading state.

**Non-Goals:**
- Completely rewrite the chat state management (we still use React useState/useCallback).
- Add real-time WebSocket syncing for sessions.
- Modify the database schema.

## Decisions

- **Decision 1: Splitting API calls in `useChatSessions`**
  - **Rationale:** Instead of a `Promise.all` loop fetching messages for every session after `/api/chat/sessions`, we will only fetch messages for the most recent session (`dbSessions[0]`). Other sessions will only be fetched on demand.
- **Decision 2: Tracking loaded sessions**
  - **Rationale:** We'll rely on the existing `messagesBySession` dictionary. If `messagesBySession[id]` is undefined, it means the session hasn't been loaded, triggering an API call and setting `isSessionLoading` to true. If it exists, we skip the network call.
- **Decision 3: Skeleton Loader UI**
  - **Rationale:** During the network request, the user shouldn't stare at an empty chat or the old messages. We'll render a visually pleasing skeleton effect in `ChatInterface.tsx` that simulates fake User and AI bubbles.

## Risks / Trade-offs

- **Risk**: A slight delay (network latency) when clicking on an older session from the sidebar compared to the old pre-loaded approach.
  - **Mitigation**: The Skeleton loader provides immediate visual feedback, making the UI feel responsive despite the delay. Once loaded, it's cached in memory.
