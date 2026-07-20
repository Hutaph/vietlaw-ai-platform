# Legal Answer Quality Evaluation

This document defines the evaluation workflow for improving legal answer
quality without changing the retrieval architecture, model weights, provider
model, API response schema, or SSE stream schema.

## Quality Stages

The evaluator separates quality into five stages:

1. Retrieval quality: whether an expected source appears in retrieved
   candidates.
2. Reranking quality: whether an expected source appears in the final top 5
   context.
3. Context quality: whether final context keeps source IDs, metadata, and
   non-empty legal text without duplicates.
4. Answer grounding: whether answer references are supported by final context.
5. Citation validity: whether cited IDs map to final context sources.

`top-5 overlap` can help detect broad behavior shifts, but it is not the main
quality metric.

## Dataset

The verified retrieval dataset is:

```text
backend/tests/fixtures/legal_retrieval_quality.jsonl
```

It currently contains 20 records with verified source IDs. Keep this dataset
focused on questions that have known corpus support so retrieval metrics remain
interpretable.

Insufficient-context answer cases are tracked separately:

```text
backend/tests/fixtures/legal_insufficient_context_quality.jsonl
```

Those records intentionally have no required source ID and use:

```json
{
  "required_source_ids": [],
  "acceptable_source_ids": [],
  "expected_behavior": "insufficient_context",
  "must_not_invent_citation": true
}
```

Each record has this shape:

```json
{
  "id": "land_transfer_conditions_001",
  "question": "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
  "required_source_ids": ["LDD_2024_D45_K1"],
  "acceptable_source_ids": [],
  "critical": true,
  "category": "land",
  "question_type": "natural_language",
  "notes": "Expected source verified against corpus metadata."
}
```

Ground-truth rules:

- Required and acceptable source IDs must exist in the tracked corpus.
- Direct citation examples may be derived from corpus metadata.
- Natural-language examples must be manually checked against clause text.
- Do not use Gemini or another model to generate ground truth.
- Do not include user logs or sensitive data.
- Do not add fake source IDs for insufficient-context cases.

The initial dataset includes the known land cases:

- `LDD_2024_D27_K3`
- `LDD_2024_D45_K1`

## Metrics

Retrieval-only reports cover only retrieval/reranking/context metrics:

- Retrieval Hit@10
- Retrieval Recall@10
- Reranker Hit@5
- Reranker Recall@5
- MRR@10
- critical miss count
- empty-context count
- duplicate final source count
- median total latency
- median TTFT when available

Answer reports additionally include:

- required citation presence rate
- invalid citations returned in the final answer
- unused-by-answer count
- unsupported-reference detector findings
- insufficient-context pass count

Citation metrics are `not_applicable` for retrieval-only runs. Do not interpret
retrieval-only `0` values as answer quality.

Failure stage values:

- `missing_from_corpus`
- `missing_from_qdrant_top10`
- `lost_during_reranking`
- `lost_during_context_building`
- `unused_by_answer`
- `invalid_citation`
- `fail_hallucinated_reference`
- `fail_overconfident`
- `fail_empty_or_error`
- `passed`

Unsupported-reference detection is diagnostic-only. Findings are conservative
string matches, not a hallucination count, and must be manually reviewed before
being used as evidence of answer correctness.

## Running Retrieval Evaluation

Start the backend with the production-like local configuration. Keep:

- candidateK = 10
- topK = 5
- semantic cache disabled
- FAISS fallback disabled
- one Uvicorn worker
- no `--reload`

Then run from `backend/`:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_retrieval_quality.jsonl \
  --retrieval-only \
  --candidate-k 10 \
  --top-k 5 \
  --output /tmp/vietlaw-quality-improvements/phase0-baseline.json
```

The retrieval evaluator runs in-process and uses the existing pipeline. It
does not add a retrieval stage or change runtime behavior.

## Running Answer Evaluation

Answer evaluation calls the running backend `/chat` endpoint and should be
limited to representative questions to control provider cost:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_retrieval_quality.jsonl \
  --answer-evaluation \
  --base-url http://127.0.0.1:8000 \
  --max-questions 10 \
  --output /tmp/vietlaw-quality-improvements/phase0-answer.json
```

The evaluator stores IDs, counts, stage traces, and timing values. It does not
write full answers or passages to tracked paths.

For insufficient-context cases:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_insufficient_context_quality.jsonl \
  --answer-evaluation \
  --base-url http://127.0.0.1:8000 \
  --output /tmp/vietlaw-quality-improvements/insufficient-context.json
```

Expected passing classifications are:

- `PASS_SAFE_FALLBACK`: answer clearly says available data is insufficient and
  does not invent a source.
- `PASS_CAUTIOUS_GUIDANCE`: answer gives general cited guidance but does not
  conclude the user's personal/legal outcome.

Failing classifications include hallucinated references, unrelated citations,
overconfident conclusions, and empty/error answers.

## Citation Sanitation

Generated citations are validated deterministically after the model response:

- valid source IDs present in final context are preserved;
- invalid citation markers are removed from final accumulated answers;
- mixed valid/invalid answers keep valid citations;
- all-invalid grounded legal claims use a short insufficient-context fallback.

For streaming responses, token-level chunks may already have been emitted before
final validation. The final accumulated response, final context payload, persisted
assistant message, and chat history retrieval use the sanitized answer. The SSE
schema is unchanged.

## Manual Review

Manual review is a small qualitative sample, not system-wide accuracy. Use:

- `0`: incorrect, unsupported, invented, or dangerously overconfident;
- `1`: mostly correct but missing important citation/condition/exception;
- `2`: grounded, cited, clear, and not overconfident.

Report the sample size and score distribution. Do not claim the manual average
is the full system accuracy.

## Corpus Integrity Audit

Run the read-only corpus audit from `backend/`:

```bash
.venv/bin/python scripts/audit_legal_corpus_integrity.py \
  --output /tmp/vietlaw-quality-improvements/corpus-integrity.json
```

The audit checks local JSON source IDs, empty text, malformed metadata, legal
identity collisions, and the known `LDD_2024_D27_K3` / `LDD_2024_D45_K1`
sources. It does not mutate PostgreSQL or Qdrant.

## Acceptance Thresholds

For behavior-changing phases:

- critical miss count must not increase;
- Retrieval Hit@10 must not decrease;
- Reranker Hit@5 must not decrease;
- MRR must not drop by more than 1%;
- invalid citations must not increase;
- unsupported legal references must not increase;
- empty context count must not increase;
- duplicate source count must not increase;
- median TTFT and total latency regression must stay within 10%.

Generated reports belong under `/tmp/vietlaw-quality-improvements/` and should
not be committed.

## Current Scope And Limitations

The quality branch keeps the existing models and pipeline architecture. It does
not re-index Qdrant, mutate PostgreSQL, add a new model call, or change API/SSE
schemas.

The current retrieval fixture has reached full hit/recall on the 20 verified
records, including `LDD_2024_D27_K3` and `LDD_2024_D45_K1`. This is not a claim
of general legal-answer accuracy. It only describes the tracked fixture.

Remaining limitations:

- answer quality is still evaluated on a small sample;
- unsupported-reference detector findings can be false positives;
- token-level streaming cannot retract chunks that were emitted before final
  validation;
- insufficient-context behavior is covered by four fixture records and unit
  tests, not exhaustive real-world coverage.
