## ADDED Requirements

### Requirement: Google final fallback configuration
The system SHALL support an optional Google AI Studio final LLM fallback controlled by environment variables.

#### Scenario: Google fallback enabled with key
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `true` and `GOOGLE_API_KEY` is configured
- **THEN** the LLM fallback chain includes a Google AI Studio chat client using `GOOGLE_FALLBACK_MODEL`.

#### Scenario: Google fallback disabled
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `false`
- **THEN** the LLM fallback chain does not include a Google AI Studio chat client.

#### Scenario: Google API key missing
- **WHEN** `ENABLE_GOOGLE_FALLBACK` is `true` but `GOOGLE_API_KEY` is empty
- **THEN** the system skips Google fallback initialization and logs that Google fallback is unavailable.

## MODIFIED Requirements

### Requirement: LLM Fallback Execution
The LLM integration (for rewriting and generation) SHALL automatically fallback through the configured provider chain if the current provider throws a timeout, rate limit, authentication, or connection exception. When Google final fallback is enabled and configured, the provider chain SHALL include Google AI Studio after the existing HuggingFace/Ollama primary and secondary providers.

#### Scenario: Primary LLM fails
- **WHEN** the primary LLM API throws an exception
- **THEN** the system catches the exception and immediately routes the prompt to the next fallback LLM instance.

#### Scenario: Existing providers fail with Google fallback configured
- **WHEN** both the HuggingFace-backed and Ollama-backed LLM instances fail
- **THEN** the system routes the same prompt to the configured Google AI Studio fallback model.

#### Scenario: Duplicate Google fallback model
- **WHEN** the selected model is already the same Google model as `GOOGLE_FALLBACK_MODEL`
- **THEN** the system MUST NOT retry the same Google model twice in the fallback chain.

### Requirement: Complete Inference Failure Handling
The system SHALL raise a clear HTTP error if every configured inference provider in the fallback chain fails sequentially.

#### Scenario: All configured LLM providers fail
- **WHEN** the final fallback model also throws an exception after all earlier providers have failed
- **THEN** the API returns an error response indicating that all inference providers are unavailable.
