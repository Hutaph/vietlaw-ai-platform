# Hybrid Inference Manager

## Purpose

This capability manages the provider policy and fallback strategies for inference models (LLM, Embeddings, Reranking). Remote deployments MUST avoid silently falling back to local providers unless explicitly configured with `local_first`.
## Requirements
### Requirement: Fallback Mode Configuration
The system SHALL support configuring inference mode via the `INFERENCE_STRATEGY` environment variable (`remote_first` or `local_first`).

#### Scenario: Inference strategy initialization
- **WHEN** the backend application starts
- **THEN** it reads the `INFERENCE_STRATEGY` variable before constructing provider chains.

#### Scenario: Remote-first does not initialize local providers
- **WHEN** `INFERENCE_STRATEGY=remote_first`
- **THEN** the backend MUST NOT initialize or fallback to Ollama local providers for LLM or embedding execution.

#### Scenario: Local-first may use local providers
- **WHEN** `INFERENCE_STRATEGY=local_first`
- **THEN** the backend MAY initialize Ollama local providers before configured remote providers.

### Requirement: LLM Fallback Execution
The LLM integration (for rewriting, memory summarization, and answer generation) SHALL automatically fallback through the configured provider chain if the current provider throws a timeout, rate limit, authentication, or connection exception. When a runtime user provider/model is configured for a role, that runtime provider/model SHALL be used as the role's primary LLM before configured server fallbacks are considered. When Google final fallback is enabled and configured, the provider chain SHALL include Google AI Studio after the existing configured providers unless it duplicates the selected runtime provider/model.

#### Scenario: Primary LLM fails
- **WHEN** the primary LLM API throws an exception
- **THEN** the system catches the exception and immediately routes the prompt to the next fallback LLM instance.

#### Scenario: Runtime selected provider fails
- **WHEN** a role uses a user-selected runtime provider/model and that provider throws an exception
- **THEN** the system routes the same prompt to the next configured fallback provider when fallback is enabled.

#### Scenario: Remote providers fail with Google fallback configured
- **WHEN** a remote LLM provider fails and Google fallback is enabled with a distinct configured model
- **THEN** the system routes the same prompt to the configured Google AI Studio fallback model.

#### Scenario: Duplicate Google fallback model
- **WHEN** the selected model is already the same Google model as `GOOGLE_FALLBACK_MODEL`
- **THEN** the system MUST NOT retry the same Google model twice in the fallback chain.

#### Scenario: Deployed usage without local provider
- **WHEN** the deployed environment has no reachable local Ollama provider and a remote runtime provider is configured
- **THEN** answer generation, rewriting, and summarization can run without requiring Ollama.

### Requirement: Embedding Provider Error Handling
The system SHALL surface HuggingFace embedding provider failures to clients instead of silently falling back to local embeddings in `remote_first`.

#### Scenario: HuggingFace embedding credentials are invalid
- **WHEN** HuggingFace embedding generation returns a 401 Unauthorized or equivalent authentication error
- **THEN** the API returns a clear error indicating the HuggingFace API key is invalid, expired, or lacks permission.

#### Scenario: HuggingFace embedding service is unavailable
- **WHEN** HuggingFace embedding generation returns a 500 Internal Server Error or equivalent server-side failure
- **THEN** the API returns a clear embedding-service error indicating HuggingFace is temporarily unavailable.

#### Scenario: Remote-first embedding does not use Ollama
- **WHEN** `INFERENCE_STRATEGY=remote_first` and HuggingFace embedding generation fails
- **THEN** the backend MUST NOT call Ollama as a secondary embedding provider.

### Requirement: Deploy-Safe Remote Reranking
The system SHALL provide a remote-only reranking strategy for deployments without local inference. The remote strategy SHALL use the same request-scoped or server-fallback Hugging Face credential policy as embedding retrieval, and it SHALL never initialize a local cross-encoder in a remote/serverless profile.

#### Scenario: Embedding-similarity reranking is selected
- **WHEN** `PIPELINE_RERANKING=embedding_similarity` in a remote/serverless profile
- **THEN** the backend reranks retrieved documents by cosine similarity between HuggingFace `BAAI/bge-m3` query/document embeddings and uses the resolved reranker credential for every remote embedding call

#### Scenario: Cross-encoder is requested in remote-first deployment
- **WHEN** `PIPELINE_RERANKING=cross_encoder` and the active profile is remote/serverless
- **THEN** the backend normalizes the strategy to embedding-similarity or rejects the configuration before serving requests, and it does not load a local artifact or call a Hugging Face text-classification endpoint

#### Scenario: Remote reranker credential is missing
- **WHEN** remote reranking is enabled and neither a request-scoped nor server fallback Hugging Face credential is available
- **THEN** the backend returns a clear authentication/configuration error before issuing a remote reranking request

### Requirement: Retrieval embedding and reranking credential routing
The system SHALL resolve embedding and reranking credentials at the request boundary, pass them explicitly through the retrieval pipeline, and use the server environment credential only as the configured fallback. Local inference paths MUST ignore remote credentials and MUST NOT call Hugging Face.

#### Scenario: Request credential is available
- **WHEN** a chat request includes a valid Hugging Face credential for a remote embedding/reranking profile
- **THEN** retrieval and remote reranking use the intended request-scoped credential consistently for the entire request

#### Scenario: Request credential is absent
- **WHEN** a remote request omits a Hugging Face credential but a server fallback credential is configured
- **THEN** both embedding retrieval and remote reranking use the server fallback without logging or persisting the raw credential

#### Scenario: Local profile has no remote credential
- **WHEN** the local profile runs with no Hugging Face credential
- **THEN** local fine-tuned embedding and reranking continue to work without attempting a Hugging Face API request

### Requirement: Complete Inference Failure Handling
The system SHALL raise a clear HTTP error if every configured inference provider in the fallback chain fails sequentially.

#### Scenario: All configured LLM providers fail
- **WHEN** the final fallback model also throws an exception after all earlier providers have failed
- **THEN** the API returns an error response indicating that all inference providers are unavailable.

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

