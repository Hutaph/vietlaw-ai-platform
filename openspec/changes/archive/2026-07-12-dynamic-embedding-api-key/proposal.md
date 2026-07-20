## Why

Vercel serverless deployments have strict size limits, making it impossible to run heavy local embedding models like `sentence-transformers`. The current codebase requires the server to provide a global HuggingFace API key for remote embeddings. To support multi-user public deployments, the system needs to allow users to provide their own HuggingFace API key (BYOK) for the embedding phase, just as they currently do for the LLM generation phase.

## What Changes

- Refactor `HuggingFaceEndpointEmbedding` to remove the startup singleton constraint, allowing it to accept a dynamic API key per request.
- Update `app/services/pipeline.py` and `app/api/chat.py` to extract the `huggingface` API key from `request.inference_config` and pass it to the embedding process.
- Implement a fallback mechanism: If the user doesn't provide a key, fallback to the server's `HUGGINGFACE_API_KEY` environment variable.
- Add explicit error handling: If both keys are missing or invalid (e.g., 401 Unauthorized), the system will catch the error and send a clear Server-Sent Event (SSE) error to the frontend UI.

## Capabilities

### New Capabilities
- `dynamic-embedding-key`: Allows the RAG pipeline to dynamically accept and use a user-provided API key for remote HuggingFace embeddings, including fallback logic and error propagation.

### Modified Capabilities


## Impact

- **Affected code:** `app/api/chat.py`, `app/services/pipeline.py`, `app/services/embedding/hf_endpoint.py`.
- **System Behavior:** Replaces the static initialization of the HuggingFace embedding endpoint with a dynamic, per-request instantiation pattern.
