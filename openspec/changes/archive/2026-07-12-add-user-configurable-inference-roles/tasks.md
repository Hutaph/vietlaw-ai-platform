## 1. Backend Runtime Configuration Models

- [x] 1.1 Add Pydantic request models for provider credentials, role assignments, and runtime inference configuration.
- [x] 1.2 Validate supported provider ids, model ids, and required API keys without accepting arbitrary base URLs.
- [x] 1.3 Add secret redaction helpers for runtime inference config in logs, validation errors, and exceptions.
- [x] 1.4 Preserve backward compatibility for existing requests that only send the flat `model` field.

## 2. Backend Provider Registry and LLM Factory

- [x] 2.1 Create a provider registry for Google AI Studio, HuggingFace Router, and optional development Ollama entries.
- [x] 2.2 Refactor LLM client creation to accept role-specific runtime provider/model/API-key configuration.
- [x] 2.3 Keep environment-based provider keys and fallback models available as server defaults.
- [x] 2.4 Ensure deployed remote providers can run without requiring a reachable local Ollama provider.
- [x] 2.5 Add duplicate provider/model de-duplication across runtime primary and configured fallbacks.

## 3. Role-Aware Pipeline Integration

- [x] 3.1 Route answer generation through the runtime `answer` role when provided.
- [x] 3.2 Pass runtime `rewriter` role configuration into query rewriting when rewriting is enabled.
- [x] 3.3 Pass runtime `summarizer` role configuration into asynchronous memory summarization when memory is enabled.
- [x] 3.4 Skip or fallback safely when helper-role LLM setup is unavailable without failing the user answer.
- [x] 3.5 Confirm retrieval and semantic cache embedding calls continue using fixed HuggingFace `BAAI/bge-m3` configuration.

## 4. Frontend Settings State

- [x] 4.1 Extend AI settings types with provider credentials, remember-on-device behavior, and role assignments.
- [x] 4.2 Store remembered provider keys in browser-local storage and session-only keys in session storage.
- [x] 4.3 Add normalization and reset helpers for provider credentials and role assignments.
- [x] 4.4 Ensure stored API keys are never displayed unmasked after save.

## 5. Frontend Setup and Role UI

- [x] 5.1 Add a first-run setup popup when no usable answer role configuration exists.
- [x] 5.2 Explain browser-local key storage and fixed server-managed embeddings in the setup popup.
- [x] 5.3 Add provider credential inputs with masked values and clear/reset controls.
- [x] 5.4 Add provider/model selectors for answer, rewriter, and summarizer roles.
- [x] 5.5 Add a control to reuse the answer provider/model for helper roles.
- [x] 5.6 Update the chat model selector to reflect provider-aware role configuration instead of a flat model-only list.

## 6. Request Flow and Proxy Handling

- [x] 6.1 Include runtime inference configuration in chat requests from the frontend.
- [x] 6.2 Forward runtime inference configuration through the Next.js chat proxy without logging secrets.
- [x] 6.3 Ensure streaming and non-streaming chat endpoints consume the same runtime config shape.
- [x] 6.4 Avoid including provider credentials in persisted chat messages, session summaries, or frontend-visible responses.

## 7. Testing and Verification

- [x] 7.1 Add backend unit tests for provider/model validation and missing API key behavior.
- [x] 7.2 Add backend tests proving runtime user keys override environment keys only for the current request.
- [x] 7.3 Add backend tests for role routing across answer, rewriter, and summarizer.
- [x] 7.4 Add backend tests that API keys are redacted from logs/errors where practical.
- [x] 7.5 Add frontend tests or script checks for provider setup completeness, role assignment persistence, and clear/reset behavior.
- [x] 7.6 Add verification that embedding provider/model cannot be overridden by runtime inference settings.

## 8. Documentation and Deployment Polish

- [x] 8.1 Update `.env.example` to clarify which variables are server defaults versus browser BYOK settings.
- [x] 8.2 Document the deployed setup flow and recommended Google AI Studio provider configuration.
- [x] 8.3 Document rollback to environment-based inference defaults.
- [x] 8.4 Validate the OpenSpec change and run relevant backend/frontend test suites.
