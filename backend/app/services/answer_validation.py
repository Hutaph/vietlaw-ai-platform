"""Deterministic answer citation validation helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


_CITE_TAG_RE = re.compile(r"<cite\s+id=[\"']([^\"']+)[\"']>(.*?)</cite>", re.IGNORECASE | re.DOTALL)
_CITE_ID_RE = re.compile(r"<cite\s+id=[\"']([^\"']+)[\"']>", re.IGNORECASE)
_LEGAL_REF_RE = re.compile(r"\b(?:Điều|Khoản|Điểm)\s+\d+", re.IGNORECASE)


@dataclass(frozen=True)
class CitationValidationResult:
    text: str
    valid_citation_ids: tuple[str, ...]
    invalid_citation_ids: tuple[str, ...]
    duplicate_citation_ids: tuple[str, ...]
    fallback_used: bool = False


def _ordered_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _context_source_ids(context: list[dict[str, Any]]) -> list[str]:
    source_ids: list[str] = []
    for item in context:
        if not isinstance(item, dict):
            continue
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("id"), str):
            source_ids.append(metadata["id"])
    return source_ids


def validate_generated_citations(answer_text: str, context: list[dict[str, Any]]) -> CitationValidationResult:
    """Remove citation markers whose IDs are not in the final context.

    The function never adds or remaps citations. It only preserves valid source IDs,
    removes invalid citation markup, and falls back when a legal answer has no valid
    grounding left.
    """
    text = answer_text or ""
    allowed_ids = set(_context_source_ids(context))
    cited_ids = _CITE_ID_RE.findall(text)
    valid_ids = _ordered_unique(source_id for source_id in cited_ids if source_id in allowed_ids)
    invalid_ids = _ordered_unique(source_id for source_id in cited_ids if source_id not in allowed_ids)
    duplicate_ids = _ordered_unique(
        source_id for source_id in cited_ids if cited_ids.count(source_id) > 1
    )

    def replace_tag(match: re.Match[str]) -> str:
        source_id = match.group(1)
        label = match.group(2)
        return match.group(0) if source_id in allowed_ids else label

    sanitized = _CITE_TAG_RE.sub(replace_tag, text)

    fallback_used = False
    has_legal_claim = bool(_LEGAL_REF_RE.search(sanitized))
    if (not allowed_ids or (cited_ids and not valid_ids and has_legal_claim)) and has_legal_claim:
        sanitized = "Dữ liệu hiện có chưa cung cấp đủ căn cứ pháp lý để trả lời chắc chắn câu hỏi này."
        fallback_used = True
        valid_ids = []

    return CitationValidationResult(
        text=sanitized,
        valid_citation_ids=tuple(valid_ids),
        invalid_citation_ids=tuple(invalid_ids),
        duplicate_citation_ids=tuple(duplicate_ids),
        fallback_used=fallback_used,
    )
