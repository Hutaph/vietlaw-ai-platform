"""
Utilities for splitting unusually long legal clauses into smaller chunks.
"""
import re


_SUB_CLAUSE_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:[a-zA-ZđĐ]\)|\d+\.)[ \t]*"
)


def _sliding_window(
    content: str,
    max_words: int,
    overlap_words: int = 50,
) -> list[str]:
    """Split content by words while retaining a small overlap."""
    words = content.split()
    if not words:
        return [content]

    overlap = min(overlap_words, max_words - 1)
    step = max_words - overlap

    chunks = []
    for start in range(0, len(words), step):
        chunk_words = words[start:start + max_words]
        if not chunk_words:
            break
        chunks.append(" ".join(chunk_words))
        if start + max_words >= len(words):
            break
    return chunks


def split_long_clause(content: str, max_words: int = 512) -> list[str]:
    """Split a long clause at sub-clause markers or by a sliding window.

    Markers such as ``a)``, ``b)`` or ``1.``, ``2.`` must appear at the
    beginning of a line. Introductory text before the first marker is kept
    with the first sub-clause.
    """
    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")

    if len(content.split()) <= max_words:
        return [content]

    marker_starts = [
        match.start() for match in _SUB_CLAUSE_PATTERN.finditer(content)
    ]
    if len(marker_starts) >= 2:
        parts = []
        start = 0
        for boundary in marker_starts[1:]:
            part = content[start:boundary].strip()
            if part:
                parts.append(part)
            start = boundary

        final_part = content[start:].strip()
        if final_part:
            parts.append(final_part)

        if len(parts) > 1:
            return parts

    return _sliding_window(content, max_words)
