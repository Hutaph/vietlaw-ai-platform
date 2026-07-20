## ADDED Requirements

### Requirement: Verified Google AI Studio chat model catalog
The system SHALL expose only verified Google AI Studio chat generation model identifiers in the selectable frontend model catalog.

#### Scenario: Gemini Flash-Lite models are available
- **WHEN** the chat model selector is rendered
- **THEN** the selector includes `gemini-3.1-flash-lite` and `gemini-2.5-flash-lite` as selectable Google AI Studio models.

#### Scenario: Unverified Gemma model is not enabled
- **WHEN** no verified Google AI Studio or Gemini API model id exists for Gemma 4 31B
- **THEN** the selector MUST NOT expose a guessed Gemma 4 31B model id as an enabled option.

### Requirement: Google selected model routing
The backend SHALL route recognized Google AI Studio chat model identifiers to the Google OpenAI-compatible endpoint using `GOOGLE_API_KEY`.

#### Scenario: User selects Gemini 3.1 Flash-Lite
- **WHEN** a chat request contains `model` equal to `gemini-3.1-flash-lite`
- **THEN** the backend creates a Google-backed chat client for `gemini-3.1-flash-lite`.

#### Scenario: User selects Gemini 2.5 Flash-Lite
- **WHEN** a chat request contains `model` equal to `gemini-2.5-flash-lite`
- **THEN** the backend creates a Google-backed chat client for `gemini-2.5-flash-lite`.

#### Scenario: Google API key is missing for selected Google model
- **WHEN** a chat request selects a Google AI Studio model and `GOOGLE_API_KEY` is empty
- **THEN** the backend MUST fail over according to the configured inference fallback strategy instead of attempting an unauthenticated Google request.

### Requirement: Embedding stack remains unchanged
Adding Google AI Studio chat models SHALL NOT change the configured embedding provider, vector dimensions, Qdrant collection schema, or ingestion flow.

#### Scenario: Google chat model is selected
- **WHEN** a user sends a chat request using a Google AI Studio model
- **THEN** retrieval still uses the existing configured embedding provider and the existing Qdrant legal corpus.
