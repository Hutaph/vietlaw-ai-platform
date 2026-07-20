"""Deterministic helpers for legal retrieval quality evaluation."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence


_CITE_ID_RE = re.compile(r"<cite\s+id=[\"']([^\"']+)[\"']>", re.IGNORECASE)
_SOURCE_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]+_\d{4}_D\d+(?:_K\d+)?\b")
_LEGAL_REF_RE = re.compile(
    r"(?:Điều\s+\d+|Khoản\s+\d+|Luật\s+[^<\d,.;:\n()]{1,80}\s+\d{4})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class QualityRecord:
    id: str
    question: str
    required_source_ids: tuple[str, ...]
    acceptable_source_ids: tuple[str, ...]
    critical: bool
    category: str
    question_type: str
    notes: str = ""
    expected_behavior: str = "grounded_answer"
    must_not_invent_citation: bool = False

    @property
    def relevant_source_ids(self) -> set[str]:
        return set(self.required_source_ids) | set(self.acceptable_source_ids)

    @property
    def is_insufficient_context(self) -> bool:
        return self.expected_behavior == "insufficient_context"


@dataclass(frozen=True)
class StageTrace:
    record_id: str
    expected_source_ids: tuple[str, ...]
    retrieved_source_ids: tuple[str, ...]
    final_context_source_ids: tuple[str, ...]
    citation_ids: tuple[str, ...] = ()
    retrieval_rank: int | None = None
    reranker_rank: int | None = None
    final_context_presence: bool = False
    citation_presence: bool = False
    invalid_citation_ids: tuple[str, ...] = ()
    unsupported_legal_references: tuple[str, ...] = ()
    insufficient_context_result: str | None = None
    failure_stage: str = "passed"
    total_ms: float | None = None
    ttft_ms: float | None = None


def _as_str_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return tuple(value)


def parse_quality_record(raw: dict[str, Any]) -> QualityRecord:
    required_fields = {
        "id",
        "question",
        "required_source_ids",
        "acceptable_source_ids",
        "critical",
        "category",
        "question_type",
    }
    missing = sorted(required_fields - set(raw))
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    if not isinstance(raw["id"], str) or not raw["id"].strip():
        raise ValueError("id must be a non-empty string")
    if not isinstance(raw["question"], str) or not raw["question"].strip():
        raise ValueError("question must be a non-empty string")
    if not isinstance(raw["critical"], bool):
        raise ValueError("critical must be a boolean")
    required = _as_str_tuple(raw["required_source_ids"], "required_source_ids")
    acceptable = _as_str_tuple(raw["acceptable_source_ids"], "acceptable_source_ids")
    expected_behavior = str(raw.get("expected_behavior", "grounded_answer"))
    if not required and not acceptable and expected_behavior != "insufficient_context":
        raise ValueError("At least one required or acceptable source ID is needed")
    return QualityRecord(
        id=raw["id"],
        question=raw["question"],
        required_source_ids=required,
        acceptable_source_ids=acceptable,
        critical=raw["critical"],
        category=str(raw["category"]),
        question_type=str(raw["question_type"]),
        notes=str(raw.get("notes", "")),
        expected_behavior=expected_behavior,
        must_not_invent_citation=bool(raw.get("must_not_invent_citation", False)),
    )


def load_quality_dataset(path: str | Path) -> list[QualityRecord]:
    records: list[QualityRecord] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(parse_quality_record(json.loads(stripped)))
            except Exception as exc:
                raise ValueError(f"Invalid dataset record at line {line_number}: {exc}") from exc
    if not records:
        raise ValueError("Quality dataset is empty")
    return records


def load_corpus_source_ids(json_data_path: str | Path) -> set[str]:
    source_ids: set[str] = set()
    for file_path in Path(json_data_path).glob("*.json"):
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        for clause in data.get("clauses", []):
            source_id = clause.get("id")
            if isinstance(source_id, str) and source_id:
                source_ids.add(source_id)
    return source_ids


def validate_dataset_sources(records: Sequence[QualityRecord], corpus_source_ids: set[str]) -> list[str]:
    missing: list[str] = []
    for record in records:
        for source_id in sorted(record.relevant_source_ids):
            if source_id not in corpus_source_ids:
                missing.append(f"{record.id}:{source_id}")
    return missing


def first_relevant_rank(source_ids: Sequence[str], relevant_source_ids: set[str]) -> int | None:
    for index, source_id in enumerate(source_ids, start=1):
        if source_id in relevant_source_ids:
            return index
    return None


def recall_at(source_ids: Sequence[str], expected_source_ids: set[str], limit: int) -> float:
    if not expected_source_ids:
        return 0.0
    hits = set(source_ids[:limit]) & expected_source_ids
    return len(hits) / len(expected_source_ids)


def extract_citation_ids(answer_text: str) -> list[str]:
    cited = _CITE_ID_RE.findall(answer_text or "")
    if cited:
        return list(dict.fromkeys(cited))
    return list(dict.fromkeys(_SOURCE_ID_RE.findall(answer_text or "")))


def invalid_citation_ids(citation_ids: Iterable[str], final_context_source_ids: Iterable[str]) -> list[str]:
    allowed = set(final_context_source_ids)
    return [source_id for source_id in dict.fromkeys(citation_ids) if source_id not in allowed]


def detect_unsupported_legal_references(answer_text: str, final_context_text: str) -> list[str]:
    """Find explicit legal references in the answer that are absent from final context text.

    This is a conservative deterministic guardrail. It is not a semantic legal
    correctness evaluator.
    """
    context_lower = (final_context_text or "").lower()
    unsupported: list[str] = []
    for match in _LEGAL_REF_RE.findall(answer_text or ""):
        normalized = " ".join(match.split())
        if normalized.lower() not in context_lower:
            unsupported.append(normalized)
    return list(dict.fromkeys(unsupported))


_INSUFFICIENT_CONTEXT_RE = re.compile(
    r"(chưa đủ|không đủ|chưa cung cấp đủ|cần cung cấp thêm|không thể xác định|chưa thể xác định)",
    re.IGNORECASE,
)
_OVERCONFIDENT_PERSONAL_RE = re.compile(
    r"(chắc chắn|đương nhiên|bạn đủ điều kiện|bạn không đủ điều kiện|anh/chị đủ điều kiện|anh/chị không đủ điều kiện)",
    re.IGNORECASE,
)


def classify_insufficient_context_answer(
    answer_text: str,
    citation_ids: Sequence[str],
    invalid_citation_ids_: Sequence[str],
    unsupported_legal_references_: Sequence[str],
) -> str:
    """Classify answer behavior for questions that intentionally lack enough facts."""
    text = answer_text or ""
    if not text.strip():
        return "FAIL_EMPTY_OR_ERROR"
    if invalid_citation_ids_:
        return "FAIL_HALLUCINATED_REFERENCE"
    if _INSUFFICIENT_CONTEXT_RE.search(text):
        return "PASS_SAFE_FALLBACK" if not citation_ids else "PASS_CAUTIOUS_GUIDANCE"
    if unsupported_legal_references_:
        return "FAIL_HALLUCINATED_REFERENCE"
    if _OVERCONFIDENT_PERSONAL_RE.search(text) and not _INSUFFICIENT_CONTEXT_RE.search(text):
        return "FAIL_OVERCONFIDENT"
    return "PASS_CAUTIOUS_GUIDANCE" if citation_ids else "FAIL_OVERCONFIDENT"


def build_stage_trace(
    record: QualityRecord,
    retrieved_source_ids: Sequence[str],
    final_context_source_ids: Sequence[str],
    citation_ids: Sequence[str] = (),
    final_context_text: str = "",
    answer_text: str = "",
    total_ms: float | None = None,
    ttft_ms: float | None = None,
    failure_stage_override: str | None = None,
) -> StageTrace:
    relevant = record.relevant_source_ids
    retrieval_rank = first_relevant_rank(retrieved_source_ids, relevant)
    reranker_rank = first_relevant_rank(final_context_source_ids, relevant)
    final_context_presence = reranker_rank is not None
    citation_presence = bool(set(citation_ids) & relevant)
    invalid_ids = invalid_citation_ids(citation_ids, final_context_source_ids)
    unsupported_refs = detect_unsupported_legal_references(answer_text, final_context_text) if answer_text else []

    insufficient_context_result = None
    if failure_stage_override:
        failure_stage = failure_stage_override
    elif record.is_insufficient_context:
        insufficient_context_result = classify_insufficient_context_answer(
            answer_text,
            citation_ids,
            invalid_ids,
            unsupported_refs,
        )
        failure_stage = "passed" if insufficient_context_result.startswith("PASS_") else insufficient_context_result.lower()
    elif retrieval_rank is None:
        failure_stage = "missing_from_qdrant_top10"
    elif not final_context_presence:
        failure_stage = "lost_during_reranking"
    elif citation_ids and not citation_presence:
        failure_stage = "unused_by_answer"
    elif invalid_ids:
        failure_stage = "invalid_citation"
    else:
        failure_stage = "passed"

    return StageTrace(
        record_id=record.id,
        expected_source_ids=tuple(sorted(relevant)),
        retrieved_source_ids=tuple(retrieved_source_ids),
        final_context_source_ids=tuple(final_context_source_ids),
        citation_ids=tuple(citation_ids),
        retrieval_rank=retrieval_rank,
        reranker_rank=reranker_rank,
        final_context_presence=final_context_presence,
        citation_presence=citation_presence,
        invalid_citation_ids=tuple(invalid_ids),
        unsupported_legal_references=tuple(unsupported_refs),
        insufficient_context_result=insufficient_context_result,
        failure_stage=failure_stage,
        total_ms=total_ms,
        ttft_ms=ttft_ms,
    )


def compute_quality_metrics(records: Sequence[QualityRecord], traces: Sequence[StageTrace]) -> dict[str, Any]:
    if len(records) != len(traces):
        raise ValueError("records and traces must have the same length")
    total = len(records)
    critical_by_id = {record.id: record.critical for record in records}
    retrieval_hits = sum(1 for trace in traces if trace.retrieval_rank is not None and trace.retrieval_rank <= 10)
    final_hits = sum(1 for trace in traces if trace.final_context_presence)
    reciprocal_ranks = [
        1.0 / trace.retrieval_rank if trace.retrieval_rank and trace.retrieval_rank <= 10 else 0.0
        for trace in traces
    ]
    invalid_count = sum(len(trace.invalid_citation_ids) for trace in traces)
    unsupported_count = sum(len(trace.unsupported_legal_references) for trace in traces)
    duplicate_count = sum(
        max(0, len(trace.final_context_source_ids) - len(set(trace.final_context_source_ids)))
        for trace in traces
    )
    empty_context_count = sum(1 for trace in traces if not trace.final_context_source_ids)
    critical_misses = sum(
        1
        for trace in traces
        if critical_by_id.get(trace.record_id) and not trace.final_context_presence
    )
    totals = [trace.total_ms for trace in traces if trace.total_ms is not None]
    ttfts = [trace.ttft_ms for trace in traces if trace.ttft_ms is not None]
    return {
        "count": total,
        "retrieval_hit_at_10": retrieval_hits / total if total else 0.0,
        "retrieval_recall_at_10": sum(
            recall_at(trace.retrieved_source_ids, set(trace.expected_source_ids), 10)
            for trace in traces
        ) / total if total else 0.0,
        "reranker_hit_at_5": final_hits / total if total else 0.0,
        "reranker_recall_at_5": sum(
            recall_at(trace.final_context_source_ids, set(trace.expected_source_ids), 5)
            for trace in traces
        ) / total if total else 0.0,
        "mrr_at_10": sum(reciprocal_ranks) / total if total else 0.0,
        "critical_miss_count": critical_misses,
        "empty_context_count": empty_context_count,
        "duplicate_final_source_count": duplicate_count,
        "invalid_citation_count": invalid_count,
        "unsupported_legal_reference_count": unsupported_count,
        "median_total_ms": median(totals) if totals else None,
        "median_ttft_ms": median(ttfts) if ttfts else None,
    }


def trace_to_dict(trace: StageTrace) -> dict[str, Any]:
    return {
        "record_id": trace.record_id,
        "expected_source_ids": list(trace.expected_source_ids),
        "retrieved_source_ids": list(trace.retrieved_source_ids),
        "final_context_source_ids": list(trace.final_context_source_ids),
        "citation_ids": list(trace.citation_ids),
        "retrieval_rank": trace.retrieval_rank,
        "reranker_rank": trace.reranker_rank,
        "final_context_presence": trace.final_context_presence,
        "citation_presence": trace.citation_presence,
        "invalid_citation_ids": list(trace.invalid_citation_ids),
        "unsupported_legal_references": list(trace.unsupported_legal_references),
        "insufficient_context_result": trace.insufficient_context_result,
        "failure_stage": trace.failure_stage,
        "total_ms": trace.total_ms,
        "ttft_ms": trace.ttft_ms,
    }
