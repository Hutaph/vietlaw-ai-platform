## Purpose
This capability allows users to bring their own API keys (BYOK) for embedding generation, removing the dependency on a server-level global key and enabling safe serverless deployments.

## Requirements

### Requirement: Dynamic User API Key for Embeddings
The system MUST extract the HuggingFace API key from the frontend request (`inferenceConfig`) and use it for generating vector embeddings during a chat session.

#### Scenario: User provides a valid HuggingFace API key
- **WHEN** a user submits a chat request with a HuggingFace API key in the `inferenceConfig`
- **THEN** the backend uses that provided API key to call the HuggingFace Inference API for embeddings instead of the server's default key.

#### Scenario: User does not provide an API key
- **WHEN** a user submits a chat request without a HuggingFace API key
- **THEN** the backend falls back to using the server's configured `HUGGINGFACE_API_KEY` environment variable.

### Requirement: Missing API Key Error Handling
The system MUST return a clear error message to the client if no API key is available for embeddings.

#### Scenario: Both User and Server API keys are missing
- **WHEN** a chat request requires HuggingFace API embeddings but neither the user nor the server configuration provides a valid API key
- **THEN** the backend aborts the request and streams an error message to the client: "Vui lòng nhập API Key HuggingFace...".

### Requirement: Invalid API Key Error Handling
The system MUST gracefully handle unauthorized errors from the HuggingFace API.

#### Scenario: The provided API key is invalid
- **WHEN** the HuggingFace API responds with a 401 Unauthorized or similar authentication error
- **THEN** the backend catches the exception and streams an error message to the client indicating the API key is incorrect.

### Requirement: HuggingFace Embedding Service Error Handling
The system MUST gracefully handle server-side HuggingFace embedding failures.

#### Scenario: HuggingFace embedding provider returns a server error
- **WHEN** the HuggingFace API responds with a 500 Internal Server Error or similar server-side failure while generating embeddings
- **THEN** the backend catches the exception and streams an error message to the client indicating the HuggingFace embedding service is temporarily unavailable.

### Requirement: Remote-First Embedding Provider Policy
The system MUST NOT use local Ollama embedding fallback while `INFERENCE_STRATEGY=remote_first`.

#### Scenario: Remote-first embedding fails
- **WHEN** `INFERENCE_STRATEGY=remote_first` and HuggingFace embedding generation fails
- **THEN** the backend reports the embedding failure to the client instead of calling the local Ollama embedding endpoint.
