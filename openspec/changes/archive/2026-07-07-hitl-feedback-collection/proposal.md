## Why

To collect human preference data (Thumbs up/down and reasoning) directly from real users, enabling the creation of high-quality datasets for Supervised Fine-Tuning (SFT) and Direct Preference Optimization (DPO). This Human-in-the-loop (HITL) capability transitions the project from a static academic model to a production-ready system capable of continuous learning and alignment.

## What Changes

- Add interactive 👍 (Thumbs Up) and 👎 (Thumbs Down) feedback buttons to each AI response in the `ChatMessage` UI component.
- Display a small modal/dropdown when 👎 is clicked to let users select a reason (e.g., "Sai luật", "Trích dẫn sai", "Không liên quan") and provide an optional text comment.
- Add a new backend endpoint `POST /api/feedback` to receive the feedback payload (including `message_id`, `session_id`, `feedback_type`, and context).
- Extend the PostgreSQL schema in `backend/app/services/storage.py` with a new `chat_feedbacks` table to persistently store this data.
- (Optional but recommended) Track implicit positive feedback, such as users clicking a "Copy" button on the AI response.

## Capabilities

### New Capabilities
- `human-feedback`: Manages the collection, transmission, and persistent storage of user preference feedback (both explicit ratings and implicit signals) on AI-generated responses.

### Modified Capabilities
None.

## Impact

- **Frontend**: Modifications to `ChatMessage.tsx` (adding UI elements for feedback), `types.ts` (new feedback payload types).
- **Backend API**: A new router/endpoint for feedback ingestion (`api/feedback.py`).
- **Database**: Adds a new table `chat_feedbacks` to PostgreSQL, schema update in `storage.py`.
- **Machine Learning**: Generates gold-standard data that can be exported later for DPO/RLHF or RAGAS evaluation workflows.
