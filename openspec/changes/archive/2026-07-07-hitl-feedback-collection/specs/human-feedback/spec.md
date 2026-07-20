## ADDED Requirements

### Requirement: Feedback Interface
The system SHALL provide interactive buttons for users to evaluate AI-generated responses directly within the chat interface.

#### Scenario: Provide explicit positive feedback
- **WHEN** the user clicks the "Thumbs Up" icon on an AI response
- **THEN** the UI visually registers the positive state and the system records an explicit positive preference.

#### Scenario: Provide explicit negative feedback with reason
- **WHEN** the user clicks the "Thumbs Down" icon on an AI response
- **THEN** the system displays a form allowing the user to select a predefined reason ("Sai luật", "Trích dẫn sai", "Không liên quan", "Khác") and enter optional text, which is then submitted to the backend.

### Requirement: Feedback Collection API
The backend MUST provide a secure endpoint to receive and process user feedback payloads.

#### Scenario: Client submits explicit feedback
- **WHEN** the frontend sends a POST request to `/api/feedback` containing the `message_id`, `session_id`, `feedback_type`, and optional reasoning
- **THEN** the API validates the payload and processes the persistence logic.

### Requirement: Persistent Storage
The system SHALL store the collected feedback relationally to support future dataset extraction for machine learning fine-tuning.

#### Scenario: Saving feedback to PostgreSQL
- **WHEN** valid feedback is received by the API
- **THEN** the system inserts or updates a record in the `chat_feedbacks` PostgreSQL table, associating it with the specific `message_id` to prevent duplicate entries for the same response.
