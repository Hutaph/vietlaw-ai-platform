## ADDED Requirements

### Requirement: Fallback Mode Configuration
The system SHALL support configuring a primary and secondary inference mode via the `INFERENCE_STRATEGY` environment variable (e.g., `remote_first`, `local_first`).

#### Scenario: Inference strategy initialization
- **WHEN** the backend application starts
- **THEN** it reads the `INFERENCE_STRATEGY` variable and prioritizes initialization of the respective Primary and Fallback model instances.

### Requirement: LLM Fallback Execution
The LLM integration (for rewriting and generation) SHALL automatically fallback to the secondary model if the primary model throws a timeout, rate limit, or connection exception.

#### Scenario: Primary LLM fails
- **WHEN** the primary LLM API throws an exception
- **THEN** the system catches the exception and immediately routes the prompt to the fallback LLM instance.

### Requirement: Complete Inference Failure Handling
The system SHALL raise a clear HTTP error if BOTH the primary and fallback inference modes fail sequentially.

#### Scenario: Both primary and fallback LLM fail
- **WHEN** the fallback model also throws an exception after the primary model has failed
- **THEN** the API returns an error response indicating that all inference providers are unavailable.
