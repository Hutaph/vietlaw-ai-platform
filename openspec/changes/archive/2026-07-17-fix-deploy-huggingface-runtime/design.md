## Context

The backend currently supports both local fine-tuned models and Hugging Face endpoint embeddings, but the deployment boundary is implicit. `backend/requirements.txt` includes local ML packages even when the runtime is configured for remote inference, so the Vercel Python function reaches approximately 4.9 GB and cannot be deployed under the 500 MB function limit.

The request path has a second deployment issue. The async pipeline contains two search-dispatch blocks and can call `QdrantSearcher.asearch()` twice for the same rewritten queries. Embedding credentials are also resolved at several layers: chat requests can provide a Hugging Face key, the embedding adapter can use the server key, and the remote embedding-similarity reranker currently constructs its own adapter from the environment key. The result is unnecessary inference traffic and a risk that retrieval and reranking use different credentials.

The intended runtime contract is:

```text
local/native or Docker
  fine-tuned embedding artifact -> Qdrant -> fine-tuned local cross-encoder

serverless deployment
  Hugging Face embedding API -> Qdrant -> Hugging Face embedding-similarity reranker
```

## Goals / Non-Goals

**Goals:**

- Make local and serverless inference profiles explicit and mutually valid.
- Keep the local fine-tuned embedding and reranker path available without weakening its artifact validation.
- Make the serverless Python dependency set lightweight enough to pass the platform function-size limit.
- Ensure one request-scoped credential policy is used consistently by embedding retrieval and remote reranking.
- Ensure each async rewritten query is searched once and preserve multi-query pooling/deduplication.
- Validate remote/local configuration early and expose actionable, redacted diagnostics.
- Add regression coverage for request counts, credential routing, mode selection, and deployment packaging inputs.

**Non-Goals:**

- Changing the Qdrant collection, vector dimension, indexed corpus, or embedding model semantics.
- Re-training or converting the fine-tuned embedding or reranker artifacts.
- Moving LLM answer generation to a new provider.
- Making Vercel serverless execute PyTorch or load local model weights.
- Introducing user accounts, a server-side secret store, or persistent storage for browser API keys.

## Decisions

### 1. Use an explicit runtime profile with compatible provider defaults

Add a deployment profile setting with two supported values, local and serverless. The local profile keeps `HUGGINGFACE_EMBEDDING_MODE=local` and `PIPELINE_RERANKING=cross_encoder`; the serverless profile uses `HUGGINGFACE_EMBEDDING_MODE=api` and `PIPELINE_RERANKING=embedding_similarity`. The profile validates or derives these provider choices rather than allowing a serverless process to silently attempt local artifacts.

Alternative considered: keep the current implicit environment combinations. This is rejected because a Hub model id in local mode, or a local cross-encoder in a serverless bundle, fails only during startup or first request and produces misleading provider errors.

### 2. Keep production dependencies in the default manifest and move local ML extras to a local profile

The default `backend/requirements.txt` will contain the dependencies required by the remote/Qdrant backend. Local-only packages such as PyTorch, Transformers, Sentence Transformers, and related weight/runtime packages will move to a separate local dependency manifest. Docker/local setup will install the base manifest plus local extras; the Vercel Python builder will install only the base manifest.

Alternative considered: maintain a separate Vercel-specific requirements file while leaving the current default manifest unchanged. This is rejected because the platform automatically discovers the default backend requirements and the current failure occurs before application code can exclude those packages.

### 3. Use one request-scoped retrieval credential object

The chat layer will resolve credentials once per request. The retrieval pipeline will receive separate embedding and reranker credential fields so that each provider has an explicit ownership boundary, while the current deployment profile may populate both from the same Hugging Face credential. Server environment credentials remain the fallback when the request does not provide one. Raw tokens will not be logged or persisted; cache identity/logging will use a redacted or non-secret fingerprint if identity is needed.

Local model providers will ignore remote credentials and must not make a Hugging Face request. Remote provider construction will fail early with a user-safe authentication error when no credential is available.

Alternative considered: let each adapter read `HUGGINGFACE_API_KEY` independently. This is rejected because request-scoped BYOK credentials then do not reliably reach the reranker and retrieval/reranking can disagree about the active token.

### 4. Make the async retrieval dispatch single-path

`RAGPipeline.aretrieve()` will have one dispatch path: call `asearch()` when supported, otherwise call synchronous `search()` in a worker thread. It will not perform a preliminary call followed by a second capability check. Qdrant will continue to embed each rewritten query once, execute the configured dense/sparse retrieval, pool results, and deduplicate before reranking.

Alternative considered: retain the duplicate call and deduplicate only documents. This is rejected because document deduplication cannot undo duplicated external API calls, latency, rate usage, or authentication failures.

### 5. Route remote reranking by capability, not by local class assumptions

The remote deployment profile will use embedding-similarity reranking, which reuses the fixed BAAI/bge-m3 embedding space. If a cross-encoder strategy is requested in serverless/remote mode, configuration will either normalize it to embedding-similarity with a diagnostic or reject it before startup; it will never attempt to load a local artifact or use an unsupported Hugging Face text-classification request shape.

Alternative considered: deploy the local cross-encoder inside the serverless function. This is rejected by the function size limit and cold-start/resource constraints.

## Risks / Trade-offs

- [Risk] Remote embedding-similarity reranking makes multiple Hugging Face embedding calls per request and may be slower or more rate-sensitive than local cross-encoder inference. → Mitigate with candidate limits, batch/document embedding where supported, request-count tests, and clear deployment defaults; local profile remains available for quality/performance testing.
- [Risk] Removing local ML packages from the default manifest could break undocumented native setup commands. → Update Docker/local setup documentation and add a verification step that installs the local extras before local-model tests.
- [Risk] Existing Qdrant data may have been indexed with a different embedding space. → Keep the model/dimension/collection contract unchanged and fail readiness on dimension or artifact mismatch rather than silently reindexing.
- [Risk] Runtime Hugging Face keys are user-provided and may be invalid or revoked. → Validate availability before remote retrieval, map 401 responses to a clear redacted error, and do not fall back to a different embedding space.
- [Risk] Serverless startup/readiness code may still try to preload local models. → Disable local preload/warmup in the serverless profile and make readiness report the active profile and remote/local requirements without exposing secrets.

## Migration Plan

1. Add the profile and credential-routing contracts, then fix the single-path async retrieval dispatch.
2. Split base and local dependency manifests; update Docker and local setup to install both where local models are enabled.
3. Configure local/native and serverless environments separately, with serverless using API embedding and embedding-similarity reranking.
4. Run unit/integration tests and a Vercel build/package-size verification before deployment.
5. Deploy the serverless profile and verify health/readiness, one chat request, semantic-cache-on/off paths, and remote reranking.

Rollback is configuration-first: restore the previous dependency manifest and runtime settings if the deployment verification fails. The serverless profile must not be rolled back to local model settings unless the backend is moved to a container runtime that includes the local extras and artifacts.

## Open Questions

- Which exact environment variable name should be the public runtime profile switch, or should the profile be derived entirely from the existing embedding/reranking mode variables?
- Should the deployed Hugging Face credential be server-owned only, or should browser BYOK continue to override it for retrieval and remote reranking?
- Does the target deployment need remote reranking enabled by default, or should it default to no reranking until Hugging Face request budgets are verified?

