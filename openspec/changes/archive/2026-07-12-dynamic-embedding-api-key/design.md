## Context

The system's embedding phase relies on `HuggingFaceEndpointEmbedding` which is instantiated as a singleton at application startup. This singleton uses the `HUGGINGFACE_API_KEY` defined in the server's `.env`. This setup works fine when deployed locally or with a dedicated backend where the server owner provides the key. However, when deployed in a serverless environment (e.g., Vercel) without a global key, the application crashes if local models cannot be loaded due to size limits. To enable public multi-user deployments without bankrupting the developer's HuggingFace API limits, the system must accept user-provided API keys (BYOK) for embedding, similar to the existing implementation for LLM generation.

## Goals / Non-Goals

**Goals:**
- Extract the HuggingFace API key from the frontend request (`request.inference_config.credentials.huggingface.api_key`).
- Dynamically instantiate or configure the embedding component per request to use this key.
- Provide a fallback mechanism to the server's environment variable if the user does not provide a key.
- Gracefully handle cases where the key is missing entirely or invalid (401 Unauthorized), propagating an appropriate error to the client via SSE.

**Non-Goals:**
- Do not refactor the LLM generation BYOK logic; it already works well.
- Do not refactor local embedding providers (`OllamaEmbedding`, `SentenceTransformers`); only the HuggingFace endpoint needs dynamic key injection.

## Decisions

1. **Refactor `_get_embedding` in `pipeline.py` to accept dynamic context:**
   - Instead of returning a singleton, `_get_embedding()` will accept an optional `api_key` parameter. Alternatively, the embedding factory methods inside `HuggingFaceEndpointEmbedding` will accept the key per invocation. Since Langchain's `HuggingFaceEndpointEmbeddings` is lightweight, creating a new instance per request with the correct API key is safe and performant.

2. **Propagate Context from `chat.py`:**
   - In `chat.py`, when calling pipeline methods (like `aretrieve` or semantic cache checks), the API key will be extracted using `request.inference_config.api_key_for("huggingface")`.

3. **Fallback Logic in `HuggingFaceEndpointEmbedding`:**
   - When instantiated, the class will prefer the passed `api_key`. If empty, it falls back to `app.config.HUGGINGFACE_API_KEY`. If both are empty, it raises a `ValueError` or custom `MissingAPIKeyError`.

## Risks / Trade-offs

- **Risk:** Instantiating the embedding model per request could add latency.
  - **Mitigation:** Since we are using the remote API endpoint (`HuggingFaceEndpointEmbeddings`), instantiation only involves saving a token string and URL, involving no network calls or disk reads. Latency impact is virtually zero.
- **Risk:** Caching logic in semantic cache might fail if the user's key is invalid.
  - **Mitigation:** Ensure error handling catches 401 exceptions early and returns a clear error to the user before attempting caching.
