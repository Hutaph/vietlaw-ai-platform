import json
from pathlib import Path

import pytest

from app.services.legal_quality_evaluation import (
    build_stage_trace,
    classify_insufficient_context_answer,
    compute_quality_metrics,
    detect_unsupported_legal_references,
    extract_citation_ids,
    invalid_citation_ids,
    load_corpus_source_ids,
    load_quality_dataset,
    parse_quality_record,
    validate_dataset_sources,
)
from scripts.evaluate_legal_quality import _compute_answer_metrics, _context_text_for_diagnostics, _metrics_for_mode
from scripts.audit_legal_corpus_integrity import audit_json_corpus


FIXTURE = Path(__file__).parent / "fixtures" / "legal_retrieval_quality.jsonl"
INSUFFICIENT_FIXTURE = Path(__file__).parent / "fixtures" / "legal_insufficient_context_quality.jsonl"


def test_quality_dataset_schema_and_sources_are_valid():
    records = load_quality_dataset(FIXTURE)
    corpus_source_ids = load_corpus_source_ids(Path(__file__).parents[1] / "data" / "processed")

    assert len(records) >= 20
    assert not validate_dataset_sources(records, corpus_source_ids)
    assert any("LDD_2024_D27_K3" in record.required_source_ids for record in records)
    assert any("LDD_2024_D45_K1" in record.required_source_ids for record in records)


def test_quality_record_requires_expected_sources():
    with pytest.raises(ValueError, match="At least one"):
        parse_quality_record({
            "id": "bad",
            "question": "question",
            "required_source_ids": [],
            "acceptable_source_ids": [],
            "critical": False,
            "category": "test",
            "question_type": "test",
        })


def test_insufficient_context_fixture_schema_is_valid():
    records = load_quality_dataset(INSUFFICIENT_FIXTURE)

    assert len(records) == 4
    assert all(record.is_insufficient_context for record in records)
    assert all(not record.required_source_ids for record in records)
    assert all(record.must_not_invent_citation for record in records)


def test_insufficient_context_records_do_not_require_expected_sources():
    record = parse_quality_record({
        "id": "insufficient",
        "question": "Điều 999 Luật Đất đai 2024 quy định gì?",
        "required_source_ids": [],
        "acceptable_source_ids": [],
        "critical": True,
        "category": "land",
        "question_type": "insufficient_context",
        "expected_behavior": "insufficient_context",
        "must_not_invent_citation": True,
    })

    assert record.is_insufficient_context is True
    assert record.relevant_source_ids == set()


def test_insufficient_context_classifier_accepts_safe_fallback_and_cautious_guidance():
    assert classify_insufficient_context_answer(
        "Dữ liệu hiện có chưa cung cấp đủ căn cứ pháp lý để trả lời chắc chắn câu hỏi này.",
        [],
        [],
        [],
    ) == "PASS_SAFE_FALLBACK"
    assert classify_insufficient_context_answer(
        "Dữ liệu hiện có chưa đủ căn cứ để xác định Điều 999 trong tài liệu.",
        [],
        [],
        ["Điều 999"],
    ) == "PASS_SAFE_FALLBACK"
    assert classify_insufficient_context_answer(
        "Cần cung cấp thêm thông tin cá nhân; có thể tham khảo điều kiện chung tại nguồn đã trích dẫn.",
        ["LNO_2023_D78_K1"],
        [],
        [],
    ) == "PASS_CAUTIOUS_GUIDANCE"


def test_insufficient_context_classifier_rejects_hallucinated_or_overconfident_answers():
    assert classify_insufficient_context_answer(
        "Theo Điều 999, bạn chắc chắn đủ điều kiện.",
        ["FAKE_2024_D999"],
        ["FAKE_2024_D999"],
        [],
    ) == "FAIL_HALLUCINATED_REFERENCE"
    assert classify_insufficient_context_answer(
        "Bạn đủ điều kiện được mua nhà ở xã hội.",
        [],
        [],
        [],
    ) == "FAIL_OVERCONFIDENT"
    assert classify_insufficient_context_answer("", [], [], []) == "FAIL_EMPTY_OR_ERROR"


def test_metrics_calculate_hits_recall_mrr_and_critical_misses():
    records = [
        parse_quality_record({
            "id": "hit",
            "question": "q1",
            "required_source_ids": ["A"],
            "acceptable_source_ids": [],
            "critical": True,
            "category": "c",
            "question_type": "direct",
        }),
        parse_quality_record({
            "id": "miss",
            "question": "q2",
            "required_source_ids": ["Z"],
            "acceptable_source_ids": ["Y"],
            "critical": True,
            "category": "c",
            "question_type": "direct",
        }),
    ]
    traces = [
        build_stage_trace(records[0], ["B", "A"], ["A"], total_ms=100.0, ttft_ms=80.0),
        build_stage_trace(records[1], ["A", "B"], ["B"], total_ms=200.0, ttft_ms=160.0),
    ]

    metrics = compute_quality_metrics(records, traces)

    assert metrics["retrieval_hit_at_10"] == 0.5
    assert metrics["reranker_hit_at_5"] == 0.5
    assert metrics["mrr_at_10"] == 0.25
    assert metrics["critical_miss_count"] == 1
    assert metrics["median_total_ms"] == 150.0
    assert metrics["median_ttft_ms"] == 120.0


def test_acceptable_sources_count_as_relevant():
    record = parse_quality_record({
        "id": "acceptable",
        "question": "q",
        "required_source_ids": ["A"],
        "acceptable_source_ids": ["B"],
        "critical": False,
        "category": "c",
        "question_type": "direct",
    })

    trace = build_stage_trace(record, ["B"], ["B"])

    assert trace.retrieval_rank == 1
    assert trace.final_context_presence is True
    assert trace.failure_stage == "passed"


def test_citation_validation_extracts_and_flags_invalid_ids():
    answer = 'Theo căn cứ <cite id="LDD_2024_D27_K3"> và LDD_2024_D45_K1.'

    citation_ids = extract_citation_ids(answer)

    assert citation_ids == ["LDD_2024_D27_K3"]
    assert invalid_citation_ids(["A", "B", "A"], ["A"]) == ["B"]


def test_unsupported_legal_reference_detection_is_conservative():
    answer = "Theo Điều 45 Luật Đất đai, người sử dụng đất phải có giấy chứng nhận."
    context = "Nguồn: Luật Đất đai 2024 | Điều 45 | Nội dung..."

    assert detect_unsupported_legal_references(answer, context) == []
    assert detect_unsupported_legal_references("Theo Điều 99 thì được miễn.", context) == ["Điều 99"]


def test_unsupported_legal_reference_detection_handles_law_name_parentheses_and_markdown():
    context = "Nguồn: Luật Nhà ở 2023 | Điều 78 | Nội dung..."
    answer = "**Luật Nhà ở 2023 (Văn bản hợp nhất 132/VBHN-VPQH 2025)** cần thêm dữ kiện."

    assert detect_unsupported_legal_references(answer, context) == []
    assert detect_unsupported_legal_references(
        'theo luật Việt Nam và <cite id="LTTPHS_2025_D3_K1">nguồn</cite>',
        context,
    ) == []


def test_answer_diagnostic_context_includes_source_metadata():
    context = _context_text_for_diagnostics([
        {
            "content": "Nội dung điều khoản.",
            "metadata": {
                "source": "Luật Đất đai 2024",
                "dieu": 45,
                "khoan": 1,
            },
        }
    ])

    assert "Luật Đất đai 2024" in context
    assert "Điều 45" in context
    assert "Khoản 1" in context
    assert detect_unsupported_legal_references(
        "Theo Luật Đất đai 2024 Điều 45 Khoản 1 thì được áp dụng.",
        context,
    ) == []
    assert detect_unsupported_legal_references("Theo Điều 99 thì được áp dụng.", context) == ["Điều 99"]


def test_answer_mode_can_override_failure_stage_for_citation_filtered_context():
    record = parse_quality_record({
        "id": "answer-trace",
        "question": "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
        "required_source_ids": ["LDD_2024_D45_K1"],
        "acceptable_source_ids": [],
        "critical": True,
        "category": "land",
        "question_type": "natural_language",
    })

    trace = build_stage_trace(
        record,
        retrieved_source_ids=["LDD_2024_D28_K1"],
        final_context_source_ids=["LDD_2024_D28_K1"],
        citation_ids=["LDD_2024_D28_K1"],
        failure_stage_override="unused_by_answer",
    )

    assert trace.failure_stage == "unused_by_answer"


def test_answer_metrics_are_reported_separately_from_retrieval_metrics():
    record = parse_quality_record({
        "id": "answer-metrics",
        "question": "Điều kiện chuyển nhượng quyền sử dụng đất là gì?",
        "required_source_ids": ["LDD_2024_D45_K1"],
        "acceptable_source_ids": [],
        "critical": True,
        "category": "land",
        "question_type": "natural_language",
    })
    cited = build_stage_trace(
        record,
        retrieved_source_ids=["LDD_2024_D45_K1"],
        final_context_source_ids=["LDD_2024_D45_K1"],
        citation_ids=["LDD_2024_D45_K1"],
    )
    unused = build_stage_trace(
        record,
        retrieved_source_ids=["LDD_2024_D28_K1"],
        final_context_source_ids=["LDD_2024_D28_K1"],
        citation_ids=["LDD_2024_D28_K1"],
        failure_stage_override="unused_by_answer",
    )

    metrics = _compute_answer_metrics([cited, unused])

    assert metrics["required_citation_presence_rate"] == 0.5
    assert metrics["unused_by_answer_count"] == 1
    assert metrics["invalid_citations_returned"] == 0
    assert metrics["insufficient_context_count"] == 0


def test_retrieval_mode_omits_answer_only_metrics():
    record = parse_quality_record({
        "id": "retrieval-metrics",
        "question": "q",
        "required_source_ids": ["A"],
        "acceptable_source_ids": [],
        "critical": False,
        "category": "c",
        "question_type": "direct",
    })
    trace = build_stage_trace(record, ["A"], ["A"])

    metrics = _metrics_for_mode([record], [trace], "retrieval")

    assert "invalid_citation_count" not in metrics
    assert "unsupported_legal_reference_count" not in metrics


def test_generated_report_helpers_do_not_require_answer_content():
    record = parse_quality_record({
        "id": "trace",
        "question": "q",
        "required_source_ids": ["A"],
        "acceptable_source_ids": [],
        "critical": False,
        "category": "c",
        "question_type": "direct",
    })

    trace = build_stage_trace(record, ["C"], ["C"], citation_ids=["X"])

    assert trace.failure_stage == "missing_from_qdrant_top10"
    assert trace.invalid_citation_ids == ("X",)


def test_corpus_integrity_audit_is_read_only(tmp_path):
    corpus_dir = tmp_path / "processed"
    corpus_dir.mkdir()
    (corpus_dir / "law.json").write_text(
        json.dumps({
            "law_info": {"law_id": "LAW_2024", "law_name": "Luật thử nghiệm"},
            "clauses": [
                {
                    "id": "LAW_2024_D1_K1",
                    "position": {"article": 1, "clause": 1},
                    "content": "Nội dung.",
                },
                {
                    "id": "LAW_2024_D2",
                    "position": {},
                    "content": "",
                },
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    report = audit_json_corpus(corpus_dir)

    assert report["json_clause_count"] == 2
    assert report["empty_text_ids"] == ["LAW_2024_D2"]
    assert report["malformed_metadata_ids"] == ["LAW_2024_D2"]
