## 1. Database & Storage Initialization

- [x] 1.1 Update `backend/app/services/storage.py` to create the `chat_sessions` table schema (with columns: session_id, summary, turn_count).
- [x] 1.2 Implement functions to `get_session_summary` and `upsert_session_summary` in `storage.py`.

## 2. Summarizer Agent Implementation

- [x] 2.1 Create a new service file `backend/app/services/memory_manager.py`.
- [x] 2.2 Implement the `summarize_session` async function that takes the old summary and new turns, invokes a lightweight LLM, and updates the database.

## 3. API Integration

- [x] 3.1 Update the `/chat` endpoint in `backend/app/api/chat.py` to fetch the `summary`, construct a sliding window prompt, and execute the background summarizer task using `asyncio.create_task`.
- [x] 3.2 Update the `/chat/stream` endpoint similarly, ensuring the background task launches just before yielding the `done` event.
