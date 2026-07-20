## Why

The current chat generation path can only fall back between HuggingFace Router and Ollama, so users still lose answer generation when both providers are unavailable or rate-limited. Google AI Studio now exposes stable Gemini Flash-Lite text models that fit this project as low-latency, low-cost fallback and selectable chat models without changing the existing embedding or Qdrant retrieval path.

## What Changes

- Add Google AI Studio text generation support for Gemini chat models while preserving the current RAG retrieval and embedding stack.
- Add Gemini 3.1 Flash-Lite and Gemini 2.5 Flash-Lite as selectable frontend chat models.
- Add Google AI Studio as an optional final LLM fallback after the configured HuggingFace/Ollama fallback chain fails.
- Keep embedding providers unchanged; Google embeddings and vector re-ingestion are explicitly out of scope.
- Treat Gemma 4 31B as unavailable until a verified Google AI Studio/Gemini API model id is confirmed.
- Add environment-driven configuration for enabling Google fallback, selecting the fallback model, and using the Google OpenAI-compatible endpoint.

## Capabilities

### New Capabilities
- `google-ai-studio-models`: Exposes verified Google AI Studio text generation models as selectable chat models and maps them to backend provider behavior.

### Modified Capabilities
- `hybrid-inference-manager`: Extend LLM fallback execution from primary/secondary provider failover to optional Google AI Studio final fallback when all configured providers fail.

## Impact

- Backend configuration in `backend/app/config.py` for Google API key, model ids, endpoint, and enablement.
- Backend LLM construction in `backend/app/services/llm.py`, reusing OpenAI-compatible clients where practical.
- Frontend model catalog in `frontend/lib/constants.ts`.
- Environment templates in `.env.example` and local `.env` guidance.
- Tests for provider ordering, disabled/missing-key behavior, and Google model option visibility.
