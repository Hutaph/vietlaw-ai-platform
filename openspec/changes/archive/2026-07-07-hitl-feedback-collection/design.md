## Context

To enhance the capabilities of the Vietnam Legal QA System, the ML team needs high-quality, domain-specific preference data (human-annotated chosen and rejected responses). Currently, interactions are logged, but there is no mechanism to capture explicit user satisfaction. Implementing a Human-in-the-loop (HITL) feedback system allows the application to naturally collect this data for future Supervised Fine-Tuning (SFT) and Direct Preference Optimization (DPO).

## Goals / Non-Goals

**Goals:**
- Provide an intuitive, low-friction UI for users to rate AI responses (👍/👎).
- Capture structured reasons for negative feedback (e.g., "Sai luật", "Trích dẫn sai") along with optional free-text comments.
- Securely store feedback data in PostgreSQL, linked to the specific chat session and message.
- Track implicit positive feedback (such as copying the response to the clipboard).

**Non-Goals:**
- Implementing the actual fine-tuning or evaluation pipeline within the application runtime.
- Forcing users to provide feedback; the system must remain entirely optional.

## Decisions

1. **Feedback UI Location**:
   - Feedback actions (Thumbs Up, Thumbs Down, Copy) will be placed at the bottom of the `ChatMessage` component for assistant messages. This follows industry standards (e.g., ChatGPT, Claude) and ensures the context is immediately visible.

2. **Negative Feedback Flow**:
   - Instead of a heavy modal that blocks the screen, clicking 👎 will reveal an inline or lightweight popover form containing a `<select>` for predefined reasons and a `<textarea>` for details. This minimizes friction.

3. **Storage Mechanism**:
   - We will create a new PostgreSQL table `chat_feedbacks` via the `storage.py` abstraction. This provides relational integrity and makes it easy to export datasets later using SQL queries (e.g., joining with full session logs if needed).

4. **Feedback Overwriting**:
   - A user can change their feedback for a given message (e.g., changing 👍 to 👎). The backend will handle this using an `ON CONFLICT (message_id)` UPSERT operation.

## Risks / Trade-offs

- **[Risk]** Feedback Spamming: A user could repeatedly click the feedback buttons, flooding the database.
  - **Mitigation**: Implement UPSERT logic based on `message_id`. Each AI response only has one final feedback state in the database.
- **[Risk]** Database Unavailability: If PostgreSQL is down (e.g., local mode without Docker), the feedback cannot be saved.
  - **Mitigation**: The API should fail gracefully (catch exceptions and return 200 OK or a soft warning) so the chat experience is not interrupted by a feedback failure.
