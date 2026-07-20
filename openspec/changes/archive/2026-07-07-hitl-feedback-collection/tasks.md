## 1. Database Schema

- [x] 1.1 Update `backend/app/services/storage.py` to include the `chat_feedbacks` table creation inside `_ensure_schema()`.
- [x] 1.2 The table must include columns: `id`, `message_id` (UNIQUE), `session_id`, `user_query`, `ai_response`, `context_used` (JSONB), `feedback_type` (SMALLINT), `reason`, `comment`, `model_used`, and `created_at`.

## 2. Backend API

- [x] 2.1 Create `backend/app/api/feedback.py` and define a Pydantic model `FeedbackRequest` for incoming feedback payloads.
- [x] 2.2 Implement a `POST /` endpoint in `feedback.py` that connects to PostgreSQL and performs an `INSERT ... ON CONFLICT (message_id) DO UPDATE` to save or update feedback.
- [x] 2.3 Register the feedback router in `backend/app/main.py` (e.g., `app.include_router(feedback.router, prefix="/api/feedback")`).

## 3. Frontend Proxy & Types

- [x] 3.1 Update `frontend/lib/types.ts` to define `FeedbackPayload` or similar interfaces needed for the API call.
- [x] 3.2 Create a Next.js API route proxy at `frontend/app/api/feedback/route.ts` to forward POST requests securely to the FastAPI backend.

## 4. Frontend UI Component

- [x] 4.1 Update `frontend/components/chat/ChatMessage.tsx` to display 👍 (Thumbs Up), 👎 (Thumbs Down), and Copy icons beneath assistant messages.
- [x] 4.2 Implement state management for the feedback actions (`feedbackStatus: 'up' | 'down' | null`).
- [x] 4.3 Create a lightweight inline form or popover that appears when 👎 is clicked, allowing the user to select a reason ("Sai luật", "Trích dẫn sai", "Không liên quan", "Khác") and enter an optional comment.
- [x] 4.4 Implement the `handleFeedbackSubmit` function that sends the payload to the Next.js API proxy and handles loading/success states.
