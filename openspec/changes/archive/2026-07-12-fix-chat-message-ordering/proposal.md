## Why

Currently, when a user sends a message and the AI responds, both messages are saved to the PostgreSQL database concurrently via `asyncio.create_task`. In `storage.py`, the `save_chat_message` function assigns a `created_at` timestamp using the database `NOW()` function. Because of the concurrent execution, a race condition occurs where the AI message might get an earlier or identical timestamp compared to the User message. When the chat interface fetches the history, it orders by `created_at ASC`, causing the AI response to occasionally display above the User query.

## What Changes

- Modify the `save_chat_message` signature in `app/services/storage.py` to accept an optional `created_at` timestamp.
- Update the SQL insert query in `save_chat_message` to use the provided `created_at` value if available, falling back to `NOW()`.
- Update the API endpoint in `app/api/chat.py` (both streaming and non-streaming responses) to explicitly generate ordered timestamps (e.g., using `datetime.utcnow()`) for the user message and AI message before saving them.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None

## Impact

- Backend: `app/api/chat.py` and `app/services/storage.py` will be modified.
- Database: `chat_messages` table records will have strictly correct and deterministic `created_at` timestamps, preventing display issues in the frontend UI.
