## 1. Modify `useChatSessions` hook (Logic)

- [x] 1.1 Add `isSessionLoading` state to the hook to track active fetching status.
- [x] 1.2 Update the startup fetching logic to only request `/api/chat/session/[id]/messages` for the first (most recent) session, leaving other sessions in `messagesBySession` uninitialized.
- [x] 1.3 Refactor `handleSelectSession` to check if `messagesBySession[id]` exists. If not, set `isSessionLoading` to true, fetch messages via `/api/chat/session/[id]/messages`, update the state, and reset `isSessionLoading`.
- [x] 1.4 Expose the new `isSessionLoading` state to the returned object of the hook.

## 2. Implement Skeleton Loader UI

- [x] 2.1 Update `ChatInterface.tsx` to receive the `isSessionLoading` prop from the `useChatSessions` hook.
- [x] 2.2 Create a `SessionSkeletonLoader` sub-component or function inside `ChatInterface.tsx` representing fake User and Assistant message bubbles.
- [x] 2.3 Add conditional rendering logic in the main chat display area to render `SessionSkeletonLoader` if `isSessionLoading` is true, otherwise render the actual messages (`ChatMessage`).
