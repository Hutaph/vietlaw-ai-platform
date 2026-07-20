## Why

The project is moving toward deployment, where local Ollama models and server-fixed API keys are not a good default for every user. Users need a browser-local bring-your-own-key setup that lets them choose supported providers and models per inference role while keeping retrieval embeddings fixed to the deployed legal corpus.

## What Changes

- Add a first-run/provider setup experience that explains the required provider configuration and guides users through entering API keys and selecting models.
- Add browser-local provider credentials for supported remote LLM providers, with user API keys stored only in the user's browser and sent to the backend per request.
- Add role-based inference settings for answer generation, query rewriting, and memory summarization.
- Keep embeddings fixed to the server-managed HuggingFace `BAAI/bge-m3` embedding stack so deployed vector indexes remain consistent.
- Update backend LLM creation so chat, rewriter, and summarizer can use runtime provider/model/API-key configuration instead of only environment variables.
- Preserve environment-based defaults/fallbacks for server operation and optional demo/admin configuration.
- Remove local Ollama as a required production path; local providers can remain optional development fallbacks but must not be required for deployed usage.

## Capabilities

### New Capabilities
- `user-configurable-inference-roles`: Browser-local provider credentials, role-based model assignment, onboarding setup, and per-request runtime inference configuration.

### Modified Capabilities
- `hybrid-inference-manager`: LLM fallback and provider selection must accept runtime user provider configuration while preserving safe server defaults.
- `google-ai-studio-models`: Google model routing must support user-provided Google API keys per request, not only `GOOGLE_API_KEY` from the server environment.
- `query-rewriting`: Query rewriting must support the user-selected rewriter provider/model role when enabled.
- `memory-manager`: Memory summarization must support the user-selected summarizer provider/model role when enabled.

## Impact

- Frontend settings storage and UI: provider setup popup, role model selectors, API key inputs, reset/clear actions, and request payload shape.
- Frontend chat request proxy: pass runtime inference configuration to backend without logging or exposing provider secrets.
- Backend API models: extend chat request validation with provider credentials and role assignments.
- Backend LLM factory: add provider registry, runtime credential handling, role-aware model creation, and secret redaction in logs/errors.
- Backend chat, query rewriting, and memory summarization flows: pass runtime inference configuration into role-specific LLM calls.
- Tests: provider config normalization, request validation, secret redaction, role routing, fallback behavior, and embedding immutability.
