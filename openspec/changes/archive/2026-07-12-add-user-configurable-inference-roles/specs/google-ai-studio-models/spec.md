## MODIFIED Requirements

### Requirement: Google selected model routing
The backend SHALL route recognized Google AI Studio chat model identifiers to the Google OpenAI-compatible endpoint using the user-provided runtime Google API key when present, or the configured server `GOOGLE_API_KEY` when runtime credentials are not provided and server fallback is allowed.

#### Scenario: User selects Gemini 3.1 Flash-Lite
- **WHEN** a chat request contains `model` equal to `gemini-3.1-flash-lite`
- **THEN** the backend creates a Google-backed chat client for `gemini-3.1-flash-lite`.

#### Scenario: User selects Gemini 2.5 Flash-Lite
- **WHEN** a chat request contains `model` equal to `gemini-2.5-flash-lite`
- **THEN** the backend creates a Google-backed chat client for `gemini-2.5-flash-lite`.

#### Scenario: Runtime Google API key is provided
- **WHEN** a chat request selects a Google AI Studio model and includes a runtime Google API key
- **THEN** the backend creates the Google-backed chat client using the runtime Google API key for that request.

#### Scenario: Google API key is missing for selected Google model
- **WHEN** a chat request selects a Google AI Studio model and neither a runtime Google API key nor a server `GOOGLE_API_KEY` is available
- **THEN** the backend MUST fail over according to the configured inference fallback strategy instead of attempting an unauthenticated Google request.

