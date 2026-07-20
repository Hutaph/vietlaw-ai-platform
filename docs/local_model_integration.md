# Local Model Integration

This backend can run the fine-tuned retrieval models from the local filesystem
without Hugging Face Hub or Hugging Face Inference API fallback in local mode.
The current runtime architecture is:

```text
local backend
-> local fine-tuned query embedding
-> existing Qdrant Cloud collection
-> local fine-tuned cross-encoder reranker
-> context builder
-> LLM selected by INFERENCE_STRATEGY
```

Qdrant Cloud stores the already-indexed legal chunk vectors. `local` embedding
mode means query embedding is local; it does not require Qdrant itself to be
local.

## Artifacts

Expected host paths:

- Embedding: `models/embedding/vietlaw-bge-m3-finetuned/best`
- Reranker candidate 002-001: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001`
- Reranker candidate 003-004: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004`
- Provisional reranker runtime path: `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`

Expected Docker container paths:

- Embedding: `/models/embedding/vietlaw-bge-m3-finetuned/best`
- Reranker candidates under `/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/`
- Provisional reranker runtime path: `/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected`

The `models/` directory is ignored by Git and must not be committed. Docker
Compose mounts it read-only into the backend and ingest containers.

`candidate-003-004` is currently used as a provisional runtime candidate through
the ignored local `selected` symlink. This is an operational choice based on
artifact compatibility and offline smoke inference only. It is not a
validation-set comparison and must not be described as the best checkpoint.
`candidate-002-001` remains available for rollback.

Current validated weight hashes:

- Embedding `model.safetensors`: `a318ac316747eab2d429692a84d17ff25f038cb3b182f159ee97e313034a0e02`
- Reranker candidate 002-001 `model.safetensors`: `6d15b6914846cd6ac1006badd256e325c93e80de975a26b46d647d7a51c0432e`
- Reranker candidate 003-004 `model.safetensors`: `bdeb8e6771c7e97dd64136317c645529f10e4060c8e0578832f3dd1b6caa7079`

## Configuration

Embedding:

```env
EMBEDDING_PROVIDER=huggingface
HUGGINGFACE_EMBEDDING_MODE=local
HUGGINGFACE_EMBEDDING_MODEL=../models/embedding/vietlaw-bge-m3-finetuned/best
EMBEDDING_DEVICE=cpu
EMBEDDING_BATCH_SIZE=32
EMBEDDING_DIMENSION=1024
EMBEDDING_NORMALIZE=true
LOCAL_MODELS_OFFLINE=true
```

Storage with an existing Qdrant Cloud collection:

```env
STORAGE_BACKEND=qdrant_postgres
POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
QDRANT_URL=<qdrant-cloud-url>
QDRANT_API_KEY=<qdrant-cloud-api-key>
QDRANT_COLLECTION=vietlaw_clauses
DISABLE_AUTO_INGEST=true
ENABLE_FAISS_FALLBACK=false
```

`QDRANT_API_KEY` authorizes vector database access only. It is not a Hugging
Face embedding or reranking API key.

Reranker:

```env
PIPELINE_RERANKING=cross_encoder
RERANKER_MODEL=../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
RERANKER_DEVICE=cpu
RERANKER_BATCH_SIZE=8
RERANKER_MAX_LENGTH=512
RERANKER_FAIL_OPEN=false
LOCAL_MODELS_OFFLINE=true
```

The backend should reference the stable `selected` path instead of a concrete
candidate directory. Switch or rollback candidates by repointing the ignored
local symlink, for example from `candidate-003-004` to `candidate-002-001`.
Do not treat smoke-test logits as a model-selection result; the best reranker
still requires evaluation on a representative validation set.

## Local-Only Behavior

When `LOCAL_MODELS_OFFLINE=true`, the runtime sets `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1` if they are not already set. Local embedding mode loads
with `SentenceTransformer(..., local_files_only=True)`. Local reranking loads
with `AutoTokenizer.from_pretrained(..., local_files_only=True)` and
`AutoModelForSequenceClassification.from_pretrained(..., local_files_only=True)`.

There is no Hugging Face API fallback for `PIPELINE_RERANKING=cross_encoder`.
If the local artifact is missing or invalid, startup/request handling raises a
clear error instead of converting the path into a Hub model id.

`INFERENCE_STRATEGY` controls the answer-generation provider ordering. With
`EMBEDDING_PROVIDER=huggingface` and `HUGGINGFACE_EMBEDDING_MODE=local`, it does
not switch query embedding to Ollama or to a Hugging Face API endpoint.

`ENABLE_FAISS_FALLBACK=false` is the safe default. Keep it disabled when serving
against Qdrant Cloud so missing collections, auth failures, schema mismatches, or
dimension errors fail clearly instead of silently querying a stale local FAISS
index. Enable it only when the FAISS index has been rebuilt with the same
fine-tuned embedding model as the active Qdrant collection.

## Validation

Validate embedding only:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/validate_local_models.py \
  --embedding-path ../models/embedding/vietlaw-bge-m3-finetuned/best \
  --skip-reranker
```

Validate a reranker candidate:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python scripts/validate_local_models.py \
  --skip-embedding \
  --reranker-path ../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected
```

Real-model pytest coverage is opt-in:

```bash
cd backend
RUN_LOCAL_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 pytest tests/test_local_models_real.py
```

Smoke-test retrieval without LLM generation by disabling semantic cache and
FAISS fallback for the process:

```bash
cd backend
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
ENABLE_SEMANTIC_CACHE=false ENABLE_FAISS_FALLBACK=false \
python - <<'PY'
from app.services.pipeline import get_pipeline

docs, _ = get_pipeline().retrieve(
    "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
    k=10,
    rerank_top_k=5,
    enable_reranker=True,
)
print("documents:", len(docs))
print("top_ids:", [doc.metadata.get("id") for doc in docs[:5]])
PY
```

This smoke path should load the local embedding, query Qdrant Cloud, run the
local selected reranker, and avoid LLM generation.

## Index and Cache Consistency

The embedding dimension is configured by `EMBEDDING_DIMENSION` and is used by
the main Qdrant dense vector and semantic cache collection. Existing Qdrant
collections with a different dimension now raise a migration error; they are
not recreated automatically.

Semantic cache collection name is configured independently with
`SEMANTIC_CACHE_COLLECTION`. Use a new cache collection when switching to a new
embedding index, for example `semantic_cache_bge_m3_ft_v1`.

If the active Qdrant Cloud collection was already created with the same
fine-tuned embedding model, do not re-index for this integration. Changing the
embedding model in the future requires a separate migration stage that re-indexes
Qdrant, rebuilds FAISS only if FAISS fallback is explicitly used, and clears or
rebuilds semantic cache. Never query a pretrained-model index with fine-tuned
query embeddings.

This runtime integration does not re-index, clear cache, or mutate production
data. Local migration/evaluation tooling is intentionally kept out of this PR
scope.

## CPU and GPU Notes

CPU inference works but can be slow, especially reranking with
the local cross-encoder. The runtime default retrieves and reranks 10
candidates, then keeps the top 5 final contexts. CPU thread and batch-size
screening on the baseline machine did not outperform the existing
`RERANKER_BATCH_SIZE=8` configuration, so no thread or batch tuning is retained.
GPU can be used by changing `EMBEDDING_DEVICE` and `RERANKER_DEVICE`, but
Docker images should not pin CUDA-specific local builds in the shared
dependency manifest.

## Rollback

- Disable reranking with `PIPELINE_RERANKING=none`.
- Repoint `models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/selected` to
  `candidates/candidate-002-001` if the provisional candidate performs poorly
  in real use.
- Point embedding and collection configuration back to the previous model/index
  pair before serving traffic.
- Do not reuse semantic cache entries across embedding model changes.
