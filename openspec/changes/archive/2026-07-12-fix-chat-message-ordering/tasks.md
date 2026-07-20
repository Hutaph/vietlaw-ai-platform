## 1. Update Database Layer

- [x] 1.1 In `app/services/storage.py`, modify `save_chat_message` to accept an optional `created_at` argument (e.g., of type `datetime`).
- [x] 1.2 In `save_chat_message`, update the SQL `INSERT` query. Use the provided `created_at` value if not None, otherwise fallback to Postgres `NOW()`.

## 2. Update API Handlers

- [x] 2.1 In `app/api/chat.py` (streaming endpoint: `chat_stream_endpoint`), generate explicit datetime objects for `user_time` and `ai_time` (where `ai_time = user_time + timedelta(milliseconds=1)`).
- [x] 2.2 Pass the explicit timestamps to the respective `save_chat_message` tasks inside `chat_stream_endpoint`.
- [x] 2.3 In `app/api/chat.py` (non-streaming endpoint: `chat_endpoint`), apply the same explicit timestamp generation logic.
- [x] 2.4 Pass the explicit timestamps to the respective `save_chat_message` tasks inside `chat_endpoint`.
