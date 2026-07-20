# Pipeline Latency Measurement

This instrumentation measures the current chat pipeline without exposing user
content or credentials in logs. It was used to compare the previous effective
20-candidate retrieval/reranking workload with the final 10-candidate runtime
default.

## Enable Timing Logs

Timing is opt-in:

```bash
PIPELINE_TIMING_ENABLED=true
```

When disabled, the backend does not emit `pipeline_timing` logs and public API
responses/SSE events are unchanged.

## Stage Definitions

- `embedding_model_load`: lazy local embedding model initialization during the request.
- `reranker_model_load`: lazy local reranker tokenizer/model initialization during the request.
- `model_load`: sum of embedding and reranker model load durations.
- `query_embedding`: query vector inference only, excluding model load.
- `qdrant_search`: Qdrant request/response and conversion into runtime documents.
- `reranking`: tokenizer, cross-encoder inference, score extraction, and sorting, excluding model load.
- `context_building`: final context selection and prompt context construction.
- `llm_time_to_first_token`: provider request start to first streamed answer token.
- `llm_stream_after_first_token`: first streamed answer token to stream completion.
- `llm_generation`: provider request start to complete non-stream response or stream completion.
- `total_time_to_first_token`: API request start to first streamed answer token.
- `total`: API request start to response completion, error, or cancellation.

## Baseline Run

Use one Uvicorn worker and do not use `--reload`:

```bash
cd backend
PIPELINE_TIMING_ENABLED=true \
HF_HUB_OFFLINE=1 \
TRANSFORMERS_OFFLINE=1 \
.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers 1
```

By default, the backend preloads and warms the local embedding/reranker before
`/readiness` returns 200:

```bash
LOCAL_MODELS_PRELOAD_ENABLED=true
LOCAL_MODELS_WARMUP_ENABLED=true
```

`/health` remains fast while preload is running. `/readiness` may take around
90 seconds on the current CPU baseline, so deployment startup/readiness
timeouts should be greater than 120 seconds. Set either flag to `false` to
restore lazy request-time model loading for a specific run.

Keep the baseline configuration unchanged:

- local fine-tuned embedding;
- Qdrant Cloud collection;
- local fine-tuned reranker;
- retrieve 10 candidates by default;
- rerank at most 10 candidates by default;
- top 5 final contexts;
- semantic cache disabled;
- FAISS fallback disabled.

For historical comparison, the measured optimization baseline used an explicit
`candidateK=20` request payload. The accepted runtime default is now
`candidateK=10`, while final `topK` remains 5.

## Client Benchmark

In another terminal:

```bash
cd backend
.venv/bin/python scripts/benchmark_pipeline_latency.py \
  --base-url http://127.0.0.1:8000 \
  --endpoint /chat/stream \
  --timeout 300
```

The script prints request IDs. Correlate them with backend log lines where
`event` is `pipeline_timing`.

Use `--candidate-k 20` only when reproducing the historical baseline. The
default benchmark payload uses the final runtime candidate count of 10.

## Measured Optimization Summary

Candidate reduction was the source of the warm latency improvement:

- warm reranking median: 59.54s -> 40.30s;
- warm total median: 73.89s -> 51.47s;
- warm TTFT median: 73.01s -> 50.94s.

Preload/warm-up moves local model initialization into startup/readiness. It
does not materially improve already-warm reranking latency. On the baseline CPU
environment, readiness took about 82.8s and the first request after readiness
reported `model_load_ms=0`.

CPU thread and reranker batch screening did not outperform the existing
threads 4 / interop 4 / batch 8 behavior, so no thread or batch tuning code is
retained.

Quality smoke checks are not a formal retrieval evaluation. The optimized
configuration retained `LDD_2024_D27_K3` for the land-transfer notarization
question, and top-5 overlap was 0.80 on two smoke queries. `LDD_2024_D45_K1`
was still missed by both the measured 20-candidate baseline and the final
10-candidate configuration.

## Log Safety

Timing payloads include request ID, endpoint, outcome, cold/warm flags, config
shape, and durations. They must not include raw user questions, retrieved
context, answer text, API keys, database credentials, Qdrant keys, provider
headers, or local model absolute paths.

## Reports

Generated baseline reports belong outside Git, for example:

```bash
/tmp/vietlaw-pipeline-latency-baseline.md
```

Do not commit logs, reports, chat answers, credentials, or model artifacts.
