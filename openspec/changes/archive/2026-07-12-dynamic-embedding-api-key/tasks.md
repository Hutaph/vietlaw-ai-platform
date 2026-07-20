## 1. Refactor Embedding Endpoint

- [x] 1.1 Update `HuggingFaceEndpointEmbedding` in `app/services/embedding/hf_endpoint.py` to raise a `ValueError` with a user-friendly message if `api_key` is completely missing.
- [x] 1.2 In `app/services/embedding/hf_endpoint.py`, ensure the fallback logic properly checks for `HUGGINGFACE_API_KEY` from config if the dynamically passed `api_key` is empty.

## 2. Refactor Pipeline Orchestration

- [x] 2.1 Update `_get_embedding` in `app/services/pipeline.py` to accept an optional `api_key: str = None` parameter and pass it to `HuggingFaceEndpointEmbedding`.
- [x] 2.2 Remove the singleton pattern `global _embedding` from `_get_embedding()` so that it can return a fresh instance with the user's dynamic key per request, or cache instances by `api_key`.

## 3. Update Chat API 

- [x] 3.1 In `app/api/chat.py` (`/chat` endpoint), extract the huggingface API key using `request.inference_config.api_key_for("huggingface")` if available, and pass it to `_get_embedding(api_key)`.
- [x] 3.2 In `app/api/chat.py` (`/chat/stream` endpoint), perform the same key extraction and pass it to `_get_embedding(api_key)`.
- [x] 3.3 Wrap the semantic cache and pipeline execution steps in a `try/except` block to catch the `ValueError` (missing key) or 401 Unauthorized exceptions, yielding a clear `_sse({"type": "error", "message": ...})` event to the user.
