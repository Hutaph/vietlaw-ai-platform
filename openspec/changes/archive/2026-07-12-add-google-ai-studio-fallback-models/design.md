## Context

The backend currently builds LLM clients in `backend/app/services/llm.py` using `ChatOpenAI` for HuggingFace Router and an OpenAI-compatible Ollama endpoint. `INFERENCE_STRATEGY` controls whether remote or local inference is tried first, and LangChain fallbacks route from the primary LLM to the secondary LLM.

Google's Gemini API exposes an OpenAI-compatible chat completions endpoint at `https://generativelanguage.googleapis.com/v1beta/openai/`, so the project can add Google AI Studio support without replacing the existing LangChain `ChatOpenAI` integration. Google documentation verifies stable model codes `gemini-3.1-flash-lite` and `gemini-2.5-flash-lite`. A verified Google AI Studio/Gemini API model code for Gemma 4 31B has not been found, so it should not be shipped as an enabled option until confirmed.

## Goals / Non-Goals

**Goals:**
- Add Gemini 3.1 Flash-Lite and Gemini 2.5 Flash-Lite as selectable chat models.
- Allow Google AI Studio models to be invoked through the backend when selected from the frontend.
- Add optional Google AI Studio final fallback after the current HuggingFace/Ollama fallback chain.
- Keep existing request and response shapes unchanged.
- Keep existing embeddings, Qdrant data, and ingestion flow unchanged.
- Make provider behavior controlled by environment variables.

**Non-Goals:**
- Do not switch embeddings to Google embedding models.
- Do not re-ingest or recreate Qdrant collections.
- Do not add unverified Gemma 4 31B as an enabled model.
- Do not replace HuggingFace or Ollama integrations.
- Do not redesign the chat UI beyond model catalog updates.

## Decisions

### Use Google's OpenAI-compatible endpoint

Use `ChatOpenAI` with `base_url=https://generativelanguage.googleapis.com/v1beta/openai/` and `api_key=GOOGLE_API_KEY` for Google AI Studio models.

Rationale: the backend already uses `ChatOpenAI`, including streaming through LangChain chains. This avoids introducing a second chat client abstraction for the first Google integration.

Alternative considered: add `langchain-google-genai` and `ChatGoogleGenerativeAI`. This is more provider-native, but adds a new dependency and may require more adaptation for parity with existing streaming and fallback behavior.

### Add Google as optional final fallback

If `ENABLE_GOOGLE_FALLBACK=true` and `GOOGLE_API_KEY` is configured, append a Google LLM to the fallback chain. For `remote_first`, order should be HuggingFace selected model, Ollama mapped model, then Google fallback model. For `local_first`, order should be Ollama mapped model, HuggingFace selected model, then Google fallback model.

Rationale: this preserves existing strategy semantics and only expands resilience when both existing providers fail.

Alternative considered: route all selected models through Google. This would surprise users choosing HuggingFace/Ollama-backed models and is broader than the requested fallback behavior.

### Treat selected Gemini model ids as Google primary models

When the frontend sends a model id that is recognized as a Google AI Studio model, construct the primary remote LLM using Google's OpenAI-compatible endpoint for that model. Fallback behavior should still work: selected Google model can fall back to Ollama/HuggingFace according to the configured strategy where applicable, and the final Google fallback should avoid duplicating the same model instance.

Rationale: Gemini models should be truly selectable, not only hidden final fallbacks.

Alternative considered: keep Gemini models only as fallback options. This would not satisfy the user-facing request to add model options.

### Only ship verified Google model ids

The model catalog should include:
- `gemini-3.1-flash-lite`
- `gemini-2.5-flash-lite`

Gemma 4 31B should remain out of the enabled catalog until a verified API model id is obtained from Google AI Studio or the Gemini API model list.

Rationale: invalid model ids produce avoidable runtime failures and confusing UX.

Alternative considered: add a guessed Gemma model id. This is brittle and would encode unverified behavior into both frontend and backend.

### Configuration shape

Add config values:
- `GOOGLE_API_KEY`
- `ENABLE_GOOGLE_FALLBACK`
- `GOOGLE_FALLBACK_MODEL`
- `GOOGLE_OPENAI_BASE_URL`

Keep defaults conservative: fallback disabled when the key is missing, fallback model defaulting to `gemini-3.1-flash-lite`, and base URL defaulting to Google's OpenAI-compatible endpoint.

## Risks / Trade-offs

- Google endpoint rate limits or regional availability may still fail -> keep existing provider chain and return the existing clear all-providers-unavailable error when every provider fails.
- Gemini models may enforce different safety or output formatting behavior -> preserve the existing legal prompt and add smoke tests for citation-compatible outputs where feasible.
- Selected Gemini model and Google fallback model may be the same -> de-duplicate fallback instances to avoid retrying the same provider/model twice.
- Google OpenAI compatibility may not support every provider-native feature -> avoid advanced Google-only features in this change; use plain chat completion behavior first.
- Gemma 4 31B may appear later under a different model id -> document it as pending verification rather than shipping a guessed id.

## Migration Plan

1. Add configuration defaults and environment template entries.
2. Add backend Google model detection and client creation.
3. Add Google final fallback construction with missing-key disabled behavior.
4. Add frontend Gemini Flash-Lite model options.
5. Add tests for model mapping and fallback ordering.
6. Rebuild Docker images and verify chat endpoints with existing providers and, when a valid key is available, Google models.

Rollback is to set `ENABLE_GOOGLE_FALLBACK=false` and remove Gemini model selections from the UI or revert this change. Existing HuggingFace/Ollama behavior remains the baseline.

## Open Questions

- What is the verified Google AI Studio/Gemini API model id for Gemma 4 31B, if it is available through the user's account?
- Should Gemini 3.1 Flash-Lite or Gemini 2.5 Flash-Lite be the default Google fallback model?
