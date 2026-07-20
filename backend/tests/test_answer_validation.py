from app.services.answer_validation import validate_generated_citations


def _context(*source_ids):
    return [{"content": "Nội dung", "metadata": {"id": source_id}} for source_id in source_ids]


def test_valid_citation_retained():
    result = validate_generated_citations(
        'Theo <cite id="LDD_2024_D45_K1">Điều 45</cite>.',
        _context("LDD_2024_D45_K1"),
    )

    assert result.text == 'Theo <cite id="LDD_2024_D45_K1">Điều 45</cite>.'
    assert result.valid_citation_ids == ("LDD_2024_D45_K1",)
    assert result.invalid_citation_ids == ()


def test_invalid_citation_marker_removed_when_answer_still_has_valid_grounding():
    result = validate_generated_citations(
        'Theo <cite id="LDD_2024_D45_K1">Điều 45</cite> và <cite id="LDD_2024_D99_K1">Điều 99</cite>.',
        _context("LDD_2024_D45_K1"),
    )

    assert '<cite id="LDD_2024_D99_K1">' not in result.text
    assert "Điều 99" in result.text
    assert '<cite id="LDD_2024_D45_K1">Điều 45</cite>' in result.text
    assert result.invalid_citation_ids == ("LDD_2024_D99_K1",)
    assert result.fallback_used is False


def test_mixed_valid_invalid_citations_keep_valid():
    result = validate_generated_citations(
        'Theo <cite id="A">Điều 1</cite> và <cite id="B">Điều 2</cite>.',
        _context("A"),
    )

    assert '<cite id="A">Điều 1</cite>' in result.text
    assert '<cite id="B">' not in result.text
    assert result.valid_citation_ids == ("A",)
    assert result.invalid_citation_ids == ("B",)
    assert result.fallback_used is False


def test_duplicate_citations_reported_once():
    result = validate_generated_citations(
        '<cite id="A">Điều 1</cite> và <cite id="A">Điều 1</cite>.',
        _context("A"),
    )

    assert result.valid_citation_ids == ("A",)
    assert result.duplicate_citation_ids == ("A",)


def test_all_invalid_legal_answer_uses_safe_fallback():
    result = validate_generated_citations(
        'Theo <cite id="B">Điều 99</cite>, người dân có nghĩa vụ nộp hồ sơ.',
        _context("A"),
    )

    assert result.fallback_used is True
    assert result.valid_citation_ids == ()
    assert "chưa cung cấp đủ căn cứ pháp lý" in result.text


def test_ordinary_numbers_do_not_trigger_fallback():
    result = validate_generated_citations(
        'Thời hạn là 45 ngày theo tài liệu tham khảo.',
        _context("A"),
    )

    assert result.fallback_used is False
    assert result.text.startswith("Thời hạn là 45 ngày")
