## ADDED Requirements

### Requirement: Runtime provider credential handling
The LLM integration SHALL accept validated runtime provider credentials for supported providers and use them only for the current request workflow.

#### Scenario: Runtime credential overrides environment key
- **WHEN** a chat request includes a valid runtime API key for the selected provider
- **THEN** the LLM client for that provider uses the runtime API key for that request.

#### Scenario: Runtime credential is missing
- **WHEN** a selected runtime provider requires an API key and neither a runtime key nor an environment fallback key is available
- **THEN** the backend returns a clear provider setup error or falls back according to the configured fallback policy.

#### Scenario: Runtime credential is redacted
- **WHEN** the backend logs provider routing or reports an inference error
- **THEN** the provider API key value MUST be redacted.

## MODIFIED Requirements

### Requirement: LLM Fallback Execution
The LLM integration (for rewriting, memory summarization, and answer generation) SHALL automatically fallback through the configured provider chain if the current provider throws a timeout, rate limit, authentication, or connection exception. When a runtime user provider/model is configured for a role, that runtime provider/model SHALL be used as the role's primary LLM before configured server fallbacks are considered. When Google final fallback is enabled and configured, the provider chain SHALL include Google AI Studio after the existing configured providers unless it duplicates the selected runtime provider/model.

#### Scenario: Primary LLM fails
- **WHEN** the primary LLM API throws an exception
- **THEN** the system catches the exception and immediately routes the prompt to the next fallback LLM instance.

#### Scenario: Runtime selected provider fails
- **WHEN** a role uses a user-selected runtime provider/model and that provider throws an exception
- **THEN** the system routes the same prompt to the next configured fallback provider when fallback is enabled.

#### Scenario: Existing providers fail with Google fallback configured
- **WHEN** both the HuggingFace-backed and Ollama-backed LLM instances fail
- **THEN** the system routes the same prompt to the configured Google AI Studio fallback model.

#### Scenario: Duplicate Google fallback model
- **WHEN** the selected model is already the same Google model as `GOOGLE_FALLBACK_MODEL`
- **THEN** the system MUST NOT retry the same Google model twice in the fallback chain.

#### Scenario: Deployed usage without local provider
- **WHEN** the deployed environment has no reachable local Ollama provider and a remote runtime provider is configured
- **THEN** answer generation, rewriting, and summarization can run without requiring Ollama.

