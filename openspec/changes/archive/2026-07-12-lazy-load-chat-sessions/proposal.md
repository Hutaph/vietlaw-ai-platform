## Why

Currently, when a user accesses the web application, the frontend invokes a `Promise.all` operation to fetch the complete message history for ALL of the user's chat sessions. This creates a severe performance bottleneck: it triggers a burst of HTTP requests, causes substantial UI delays on startup, and unnecessarily drains backend and database resources. As users accumulate more sessions, this architecture will become completely unsustainable. Furthermore, switching sessions feels instantaneous (because they are preloaded), but it lacks visual feedback for network loading which we will need when transitioning to lazy loading.

## What Changes

- Refactor `useChatSessions.ts` to implement lazy loading for chat sessions.
- Modify the startup logic to fetch ONLY the session metadata (ID, title, timestamp) and the messages for the most recently active session.
- Add an `isSessionLoading` state to manage the fetching phase when switching sessions.
- Create a Skeleton loading effect UI in `ChatInterface.tsx` to display placeholder components while a session's messages are being fetched.
- Ensure that once a session is loaded, it is cached in the frontend state to prevent redundant API calls when the user switches back.

## Capabilities

### New Capabilities
- `lazy-chat-loading`: Introduces lazy loading and skeleton visual effects for the chat interface, improving application startup speed and UX.

### Modified Capabilities
- None.

## Impact

- Frontend: `hooks/use-chat-sessions.ts` will undergo significant state and fetching logic modifications.
- Frontend: `components/chat/ChatInterface.tsx` will be updated to handle and render the `isSessionLoading` state via a Skeleton loader.
- Backend: Less pressure on the `/api/chat/session/[id]/messages` endpoint, as it will be called incrementally rather than in massive parallel bursts.
