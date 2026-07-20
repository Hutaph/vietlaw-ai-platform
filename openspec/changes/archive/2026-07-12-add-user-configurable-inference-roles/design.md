## Context

The current deployment shape is mostly server-owned: the frontend sends a flat `model` string, while provider credentials, fallback behavior, and Google routing are controlled by environment variables in the backend. That worked for local development, but it is awkward for deployment because local Ollama models are not a reliable production default and different users may need to bring their own Google AI Studio or HuggingFace credentials.

The RAG retrieval stack has a different constraint. Embeddings and vector indexes must remain aligned, so deployed retrieval should keep using the fixed HuggingFace `BAAI/bge-m3` embedding stack and must not allow per-user embedding model changes from the chat UI.

## Goals / Non-Goals

**Goals:**
- Let users configure supported remote LLM providers and API keys in browser storage.
- Let users assign provider/model choices per inference role: answer generation, query rewriting, and memory summarization.
- Send runtime inference configuration to the backend per request without persisting user secrets server-side.
- Keep embeddings fixed to HuggingFace `BAAI/bge-m3` and preserve the deployed vector index contract.
- Preserve environment-based defaults/fallbacks for admin/demo operation and safer rollback.
- Avoid requiring local Ollama for deployed usage.

**Non-Goals:**
- Server-side encrypted API key storage.
- User accounts, authentication, billing, quota management, or key sharing across devices.
- Runtime embedding model/provider switching.
- Arbitrary custom OpenAI-compatible base URLs from untrusted users.
- Replacing the existing RAG retrieval, citation, semantic cache, or storage architecture.

## Decisions

### Store user provider keys only in browser storage

User-provided provider API keys will be stored in the browser, with an explicit "remember on this device" behavior. If remembering is disabled, the frontend can use session-scoped storage. The backend receives keys only in the current request, uses them in memory, and must not store, echo, or log them.

Rationale: the app does not currently have user accounts or a secure server-side secret store. Browser-local BYOK matches the deployment goal without introducing auth and encryption scope.

Alternative considered: store keys encrypted in PostgreSQL. This would improve cross-device UX, but it requires identity, encryption key management, rotation, and access control that are outside this change.

### Use role-based inference configuration

The frontend will model inference as roles:
- `answer`: final legal answer generation.
- `rewriter`: query classification and rewrite.
- `summarizer`: session memory summarization.

Each role points to a supported provider and model. Provider credentials are configured once per provider and reused by roles.

Rationale: answer generation, rewriting, and summarization have different cost/latency/quality needs. A single global model hides those trade-offs and makes deployment less flexible.

Alternative considered: keep a single model selector. This is simpler, but it cannot express a cheap rewriter with a stronger answer model or a lightweight summarizer.

### Use an allowlisted provider registry

The backend will validate runtime provider/model selections against a provider registry. Initial supported production providers should include Google AI Studio and HuggingFace Router. Ollama can remain as an optional development/provider fallback, but deployed setup must not require it.

Provider entries define:
- provider id.
- display name.
- OpenAI-compatible base URL or provider-specific client details.
- supported chat model ids.
- whether API key is required.
- whether the provider is intended for deployment or development.

Rationale: this prevents arbitrary user-controlled base URLs and keeps provider validation consistent across frontend and backend.

Alternative considered: allow users to enter any OpenAI-compatible base URL. This is flexible, but it creates SSRF and support risks for a deployed app.

### Keep embedding server-owned and fixed

The setup UI will explain that embeddings are handled by the server and fixed to HuggingFace `BAAI/bge-m3`. The chat request will not accept runtime embedding provider/model overrides.

Rationale: vector retrieval quality depends on using the same embedding model for indexing and querying. Runtime user changes would silently break retrieval.

Alternative considered: expose embedding selection in advanced settings. This is rejected for deployment because it would require reindexing and separate vector collections per embedding model.

### Preserve server defaults and fallback behavior

If user runtime configuration is missing, the backend may use configured environment defaults where available. If a selected user provider fails, the backend can use the configured fallback chain only when fallback is enabled and safe. Missing API keys should produce clear setup errors for required roles.

Rationale: this supports demos, local development, and gradual rollout while keeping the BYOK path explicit.

Alternative considered: require user configuration for every request and remove env fallback. This is cleaner but would make initial rollout and automated testing more brittle.

### Add a first-run setup gate

The frontend should show a setup popup when no usable answer role/provider configuration exists. The popup should explain what the user needs to configure, distinguish browser-local API key storage from server-side storage, and provide a way to test provider connectivity.

Rationale: without setup guidance, deployed users will see backend inference failures before understanding that provider configuration is required.

Alternative considered: place everything only in admin settings. This hides the critical first-run path and makes the app feel broken on first visit.

## Risks / Trade-offs

- Browser storage exposes keys to anyone with access to the browser profile or malicious injected scripts -> keep the app free of third-party script injection, document browser-local storage clearly, and provide clear/reset controls.
- Per-request API keys may appear in logs if request bodies are logged -> avoid logging raw request bodies, redact provider credentials in validation errors and backend logs, and avoid echoing config in responses.
- Runtime role configuration can drift from frontend catalog -> maintain shared provider ids/model ids and backend validation tests.
- User-selected rewriter/summarizer models may be weaker than defaults -> provide sensible defaults and "use same provider/model for helper roles" UI.
- Existing async summarization may lack access to request-time config after response completion -> pass a sanitized role config object into the background task and avoid retaining more secret material than needed.
- Semantic cache may reuse answers generated with different providers/models -> consider whether provider/model metadata should be included in cache records or whether existing cache behavior is acceptable for equivalent legal answers.

## Migration Plan

1. Introduce provider registry and runtime config models while preserving the existing `model` request field.
2. Add frontend browser-local provider credentials and role settings with defaults that mirror current behavior where possible.
3. Update answer generation to prefer runtime `answer` role config.
4. Update query rewriting to accept runtime `rewriter` role config when enabled.
5. Update memory summarization to accept runtime `summarizer` role config when enabled.
6. Add setup popup and connection validation.
7. Keep environment variables as fallback/defaults during rollout.

Rollback is to ignore runtime inference config on the backend and rely on the current environment-based provider behavior. Browser-local settings can remain harmless if the backend does not consume them.

## Open Questions

- Should the initial setup default all roles to the same provider/model, or force users to review each role?
- Should semantic cache keys include answer model/provider metadata?
- Which HuggingFace Router models should be exposed as deploy-supported defaults?
- Should Google AI Studio be the recommended default provider in the popup?
