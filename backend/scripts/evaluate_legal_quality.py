"""Evaluate legal retrieval quality against a small verified dataset.

Generated reports should be written outside the repository, for example under
`/tmp/vietlaw-quality-improvements/`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path
import sys
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import JSON_DATA_PATH, RETRIEVER_CANDIDATE_K, RETRIEVER_K
from app.services.knowledge_base import load_knowledge_base
from app.services.legal_quality_evaluation import (
    build_stage_trace,
    compute_quality_metrics,
    extract_citation_ids,
    load_corpus_source_ids,
    load_quality_dataset,
    trace_to_dict,
    validate_dataset_sources,
)
from app.services.pipeline import get_pipeline, init_pipeline, preload_local_models
from app.services.pipeline_timing import (
    PipelineTimingCollector,
    reset_current_timing,
    set_current_timing,
)


def _chat_payload(question: str, model: str, candidate_k: int, top_k: int) -> dict:
    return {
        "messages": [{"role": "user", "content": question}],
        "model": model,
        "category": "all",
        "topK": top_k,
        "candidateK": candidate_k,
        "enableQueryRewriter": False,
        "enableReranker": True,
        "enableSemanticCache": False,
        "enableMemory": False,
    }


def _post_json(base_url: str, endpoint: str, payload: dict, timeout: float) -> tuple[dict, float]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        f"{base_url.rstrip('/')}{endpoint}",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": f"quality-{uuid.uuid4()}",
        },
    )
    start = time.perf_counter()
    with request.urlopen(req, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data, (time.perf_counter() - start) * 1000


def _context_text_for_diagnostics(context_items: list[dict]) -> str:
    parts: list[str] = []
    for item in context_items:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {}
        source = metadata.get("source") or metadata.get("law")
        article = metadata.get("dieu")
        clause = metadata.get("khoan")
        header_parts = []
        if source:
            header_parts.append(str(source))
        if article:
            header_parts.append(f"Điều {article}")
        if clause:
            header_parts.append(f"Khoản {clause}")
        if header_parts:
            parts.append(" | ".join(header_parts))
        content = item.get("content", "")
        if isinstance(content, str) and content:
            parts.append(content)
    return "\n".join(parts)


async def _evaluate_retrieval(records, candidate_k: int, top_k: int, max_questions: int | None) -> tuple[list, list]:
    load_knowledge_base()
    init_pipeline()
    preload_local_models(warmup=False)
    pipeline = get_pipeline()
    traces = []
    raw_results = []
    selected_records = records[:max_questions] if max_questions else records
    for record in selected_records:
        collector = PipelineTimingCollector(
            request_id=f"quality-{record.id}",
            endpoint="in_process_retrieval",
            streaming=False,
            enabled=False,
        )
        token = set_current_timing(collector)
        start = time.perf_counter()
        try:
            docs, context = await pipeline.aretrieve(
                query=record.question,
                k=candidate_k,
                rerank_top_k=top_k,
                category="all",
                domain="legal",
                queries=[record.question],
                enable_reranker=True,
                context_token_budget=None,
            )
        finally:
            reset_current_timing(token)
        total_ms = (time.perf_counter() - start) * 1000
        metrics = collector.payload("success")["metrics"]
        retrieved_ids = metrics.get("retrieved_source_ids", [])
        final_ids = [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")]
        trace = build_stage_trace(
            record,
            retrieved_source_ids=retrieved_ids,
            final_context_source_ids=final_ids,
            final_context_text=context,
            total_ms=total_ms,
        )
        traces.append(trace)
        raw_results.append({
            "record_id": record.id,
            "timing_metrics": metrics,
            "durations_ms": collector.payload("success")["durations_ms"],
        })
    return traces, raw_results


def _evaluate_answers(records, base_url: str, model: str, candidate_k: int, top_k: int, timeout: float, max_questions: int):
    traces = []
    raw_results = []
    for record in records[:max_questions]:
        try:
            data, total_ms = _post_json(
                base_url,
                "/chat",
                _chat_payload(record.question, model, candidate_k, top_k),
                timeout,
            )
        except error.HTTPError as exc:
            raw_results.append({"record_id": record.id, "error": f"HTTP {exc.code}"})
            traces.append(build_stage_trace(record, [], [], total_ms=None))
            continue
        context_items = data.get("contextUsed", [])
        final_ids = [
            item.get("metadata", {}).get("id")
            for item in context_items
            if isinstance(item, dict) and item.get("metadata", {}).get("id")
        ]
        context_text = _context_text_for_diagnostics(context_items)
        answer_text = data.get("text", "")
        citation_ids = extract_citation_ids(answer_text)
        relevant_ids = record.relevant_source_ids
        failure_stage_override = None
        if relevant_ids and not (set(final_ids) & relevant_ids):
            # /chat returns contextUsed after citation filtering, not the raw retrieval trace.
            # Do not label answer-mode misses as Qdrant retrieval failures.
            failure_stage_override = "unused_by_answer"
        trace = build_stage_trace(
            record,
            retrieved_source_ids=final_ids,
            final_context_source_ids=final_ids,
            citation_ids=citation_ids,
            final_context_text=context_text,
            answer_text=answer_text,
            total_ms=total_ms,
            failure_stage_override=failure_stage_override,
        )
        traces.append(trace)
        raw_results.append({
            "record_id": record.id,
            "status": "ok",
            "context_count": len(final_ids),
            "citation_ids": citation_ids,
            "total_ms": round(total_ms, 3),
        })
    return traces, raw_results


def _compute_answer_metrics(traces: list) -> dict:
    total = len(traces)
    invalid_count = sum(len(trace.invalid_citation_ids) for trace in traces)
    unsupported_count = sum(len(trace.unsupported_legal_references) for trace in traces)
    required_cited = sum(1 for trace in traces if trace.citation_presence)
    insufficient_results = [
        trace.insufficient_context_result
        for trace in traces
        if trace.insufficient_context_result
    ]
    return {
        "count": total,
        "required_citation_presence_rate": required_cited / total if total else 0.0,
        "invalid_citations_returned": invalid_count,
        "unsupported_legal_reference_count": unsupported_count,
        "unused_by_answer_count": sum(1 for trace in traces if trace.failure_stage == "unused_by_answer"),
        "invalid_model_citation_count": sum(1 for trace in traces if trace.failure_stage == "invalid_citation"),
        "insufficient_context_count": len(insufficient_results),
        "insufficient_context_pass_count": sum(
            1 for result in insufficient_results if result.startswith("PASS_")
        ),
    }


def _metrics_for_mode(records: list, traces: list, mode: str) -> dict:
    metrics = compute_quality_metrics(records, traces)
    if mode == "retrieval":
        metrics.pop("invalid_citation_count", None)
        metrics.pop("unsupported_legal_reference_count", None)
    return metrics


def _write_report(output: Path, payload: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate legal answer retrieval quality.")
    parser.add_argument("--dataset", default="tests/fixtures/legal_retrieval_quality.jsonl")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--candidate-k", type=int, default=RETRIEVER_CANDIDATE_K)
    parser.add_argument("--top-k", type=int, default=RETRIEVER_K)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--output", default="/tmp/vietlaw-quality-improvements/evaluation.json")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--answer-evaluation", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument("--model", default="gemini-3.1-flash-lite")
    args = parser.parse_args()

    records = load_quality_dataset(args.dataset)
    missing = validate_dataset_sources(records, load_corpus_source_ids(JSON_DATA_PATH))
    if missing:
        raise SystemExit(f"Dataset references missing corpus source IDs: {', '.join(missing)}")

    if args.validate_only:
        payload = {
            "mode": "validate_only",
            "dataset_count": len(records),
            "missing_source_ids": [],
        }
        _write_report(Path(args.output), payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not args.answer_evaluation:
        traces, raw_results = asyncio.run(
            _evaluate_retrieval(records, args.candidate_k, args.top_k, args.max_questions)
        )
        mode = "retrieval"
    else:
        traces, raw_results = _evaluate_answers(
            records,
            args.base_url,
            args.model,
            args.candidate_k,
            args.top_k,
            args.timeout,
            args.max_questions or 10,
        )
        mode = "answer"

    evaluated_records = records[:len(traces)]
    payload = {
        "mode": mode,
        "candidate_k": args.candidate_k,
        "top_k": args.top_k,
        "metrics": _metrics_for_mode(evaluated_records, traces, mode),
        "answer_metrics": _compute_answer_metrics(traces) if mode == "answer" else "not_applicable",
        "traces": [trace_to_dict(trace) for trace in traces],
        "raw_results": raw_results,
    }
    _write_report(Path(args.output), payload)
    print(json.dumps({"output": args.output, "metrics": payload["metrics"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
