## Why

The deployed Python serverless function cannot be built because the backend bundles local ML dependencies and exceeds the platform's 500 MB function limit. At runtime, the chat retrieval path can also issue duplicate asynchronous searches and route embedding/reranking requests through inconsistent Hugging Face credentials, producing repeated inference calls and intermittent `401 Unauthorized` responses.

The system needs an explicit split between local quality runtime and deployment-safe runtime: local development must keep using the fine-tuned embedding and reranker artifacts, while the deployed backend must use a lightweight Hugging Face API path with deterministic credential handling.

## What Changes

- Add explicit local and deployment runtime profiles for embedding and reranking.
- Keep the fine-tuned local embedding and cross-encoder reranker available for native/Docker local execution.
- Add a deployment-safe dependency path that does not install PyTorch, Transformers, or Sentence Transformers into the serverless function bundle.
- Route deployed embedding and remote reranking through Hugging Face with one validated credential source per request.
- Remove the duplicate async retrieval invocation so each rewritten query generates one embedding/search operation.
- Ensure the remote embedding-similarity reranker receives the same intended Hugging Face credential as retrieval when request-scoped credentials are enabled.
- Add configuration validation and runtime diagnostics for invalid mode/model combinations, missing remote credentials, and deployment-incompatible local model settings.
- Add regression tests for request deduplication, credential routing, local/API mode selection, and deployment dependency configuration.

## Capabilities

### New Capabilities

- `deployment-runtime-profiles`: Define the supported local fine-tuned-model profile and the lightweight remote Hugging Face deployment profile, including their configuration and dependency boundaries.

### Modified Capabilities

- `hybrid-inference-manager`: Clarify embedding and reranking provider selection, request/server credential precedence, Hugging Face authentication handling, and deployment-safe remote reranking.
- `retrieval-persistence`: Require the async retrieval pipeline to execute each query once while preserving multi-query pooling and deduplication semantics.

## Impact

- Backend runtime configuration in `backend/app/config.py` and `.env.example`.
- Embedding provider construction and error handling in `backend/app/services/embedding/`.
- Retrieval orchestration in `backend/app/services/pipeline.py` and Qdrant search integration.
- Remote embedding-similarity reranking in `backend/app/services/reranking/embedding_similarity.py` and reranker interfaces.
- Chat request credential routing in `backend/app/api/chat.py` and related models.
- Python dependency manifests and Vercel/serverless packaging configuration, especially `backend/requirements.txt` and `vercel.json`.
- Backend regression tests and deployment verification documentation.

