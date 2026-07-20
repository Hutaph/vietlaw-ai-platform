## 1. Runtime Profiles and Configuration

- [x] 1.1 Add the explicit local/serverless runtime profile setting and validate its allowed values during backend configuration loading.
- [x] 1.2 Implement profile compatibility validation for embedding mode, embedding model path, reranking strategy, local preload/warmup, and required Hugging Face credentials without logging secrets.
- [x] 1.3 Update the pipeline factory so the serverless profile selects Hugging Face embedding-similarity reranking and never constructs a local cross-encoder, while the local profile retains fine-tuned local artifacts.
- [x] 1.4 Make readiness and startup diagnostics profile-aware, including active profile and redacted configuration errors; disable local model preload/warmup requirements for serverless mode.
- [x] 1.5 Update `.env.example`, Docker environment configuration, README deployment instructions, and local-model instructions for both profiles.

## 2. Embedding and Reranking Credential Routing

- [x] 2.1 Define a request-scoped retrieval credential contract with separate embedding and reranker fields and a server environment fallback policy.
- [x] 2.2 Update chat endpoints, pipeline retrieval methods, and Qdrant search methods to resolve and pass embedding credentials exactly once per request.
- [x] 2.3 Update the reranker interface and implementations so remote embedding-similarity reranking receives its resolved credential while local rerankers ignore remote credentials.
- [x] 2.4 Refactor Hugging Face embedding construction and error mapping to fail clearly on missing/invalid credentials, preserve local-mode behavior, and avoid exposing raw tokens in logs or cache identity.
- [x] 2.5 Add request-count-safe remote embedding behavior for embedding-similarity reranking, including batching or bounded candidate processing where supported.

## 3. Retrieval Dispatch and Regression Fixes

- [x] 3.1 Remove the duplicate capability-detection/search block from `RAGPipeline.aretrieve()` and retain one async dispatch path with a synchronous worker fallback only when `asearch()` is unavailable.
- [x] 3.2 Verify that each rewritten query is embedded and searched once while multi-query result pooling, document deduplication, and reranking order remain unchanged.
- [x] 3.3 Add regression tests that assert one `asearch()` invocation per retrieval operation and detect duplicate Hugging Face embedding calls caused by orchestration.
- [x] 3.4 Add regression tests covering local mode without Hugging Face credentials, serverless mode without local artifacts, request credential precedence, server fallback credentials, and redacted error handling.

## 4. Deployment Dependency Isolation

- [x] 4.1 Split the backend dependency manifests so production/serverless requirements exclude PyTorch, Transformers, Sentence Transformers, and local model runtime packages.
- [x] 4.2 Add the local ML dependency manifest and update Docker/local setup to install base requirements plus local extras when fine-tuned models are enabled.
- [x] 4.3 Update Vercel/serverless configuration and deployment documentation to use the lightweight production manifest and remote profile environment variables.
- [x] 4.4 Add a dependency verification script or test that fails if local-only ML packages re-enter the serverless requirements.

## 5. Verification and Handoff

- [ ] 5.1 Run the focused backend unit tests for configuration, embedding, reranking, pipeline dispatch, and Qdrant retrieval.
- [ ] 5.2 Run the frontend build and backend import/startup checks using the serverless profile with local artifacts absent.
- [ ] 5.3 Run a deployment package/build verification and confirm the generated serverless bundle is below the platform limit.
- [ ] 5.4 Run a local/Docker smoke test using the fine-tuned embedding and reranker artifacts and confirm no Hugging Face embedding/reranking request is made.
- [x] 5.5 Record verification results, remaining deployment environment requirements, and rollback instructions in the change documentation.
