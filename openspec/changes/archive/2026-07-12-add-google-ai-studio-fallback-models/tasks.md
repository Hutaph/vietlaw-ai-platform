## 1. Configuration

- [x] 1.1 Add Google AI Studio configuration values to `backend/app/config.py`: `GOOGLE_API_KEY`, `ENABLE_GOOGLE_FALLBACK`, `GOOGLE_FALLBACK_MODEL`, and `GOOGLE_OPENAI_BASE_URL`.
- [x] 1.2 Update `.env.example` with Google fallback settings and comments explaining that embeddings remain unchanged.
- [x] 1.3 Review local `.env` guidance so Google fallback can be enabled without exposing secrets in committed files.

## 2. Backend LLM Integration

- [x] 2.1 Add a recognized Google chat model set containing `gemini-3.1-flash-lite` and `gemini-2.5-flash-lite`.
- [x] 2.2 Add a Google `ChatOpenAI` factory using the Google OpenAI-compatible base URL and `GOOGLE_API_KEY`.
- [x] 2.3 Route selected Google model ids to the Google-backed client when a valid key is configured.
- [x] 2.4 Preserve existing HuggingFace and Ollama model mapping for non-Google selected models.
- [x] 2.5 Append Google AI Studio as a final fallback only when enabled and configured.
- [x] 2.6 De-duplicate fallback entries so the same Google model is not retried twice.
- [x] 2.7 Ensure missing Google credentials skip Google initialization and continue existing fallback behavior.

## 3. Frontend Model Catalog

- [x] 3.1 Add Gemini 3.1 Flash-Lite to `frontend/lib/constants.ts`.
- [x] 3.2 Add Gemini 2.5 Flash-Lite to `frontend/lib/constants.ts`.
- [x] 3.3 Do not add Gemma 4 31B until a verified Google AI Studio/Gemini API model id is available.

## 4. Tests

- [x] 4.1 Add backend tests for Google model detection and Google client construction behavior.
- [x] 4.2 Add backend tests for `remote_first` fallback ordering with Google as final fallback.
- [x] 4.3 Add backend tests for `local_first` fallback ordering with Google as final fallback.
- [x] 4.4 Add backend tests for missing Google key behavior.
- [x] 4.5 Add frontend or unit-level verification that the two Gemini Flash-Lite models appear in the model catalog.

## 5. Verification

- [x] 5.1 Run backend tests covering LLM configuration and fallback behavior.
- [x] 5.2 Run frontend type/build checks for the model catalog update.
- [x] 5.3 Rebuild Docker images and confirm backend startup still initializes Qdrant/Postgres and the RAG pipeline.
- [x] 5.4 Manually verify chat behavior with existing non-Google models.
- [x] 5.5 Manually verify Gemini model selection and Google final fallback when a valid `GOOGLE_API_KEY` is available.
