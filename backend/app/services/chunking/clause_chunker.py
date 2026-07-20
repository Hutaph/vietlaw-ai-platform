"""
Clause Chunker — Chunk theo điều khoản và tách nhỏ khoản quá dài.
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from app.services.chunking.sub_clause_splitter import split_long_clause
from app.services.knowledge_base import determine_category
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.chunking.clause")


def _build_embedding_content(
    law_name: str,
    position: Dict[str, Any],
    content: str,
) -> str:
    """Add available legal context to the text sent to the embedding model."""
    article_num = position.get("article")
    article_title = position.get("article_title")

    article_parts = []
    if article_num not in (None, ""):
        article_parts.append(f"Điều {article_num}")
    if article_title:
        article_parts.append(str(article_title))

    prefix_parts = []
    if law_name:
        prefix_parts.append(str(law_name))
    if article_parts:
        prefix_parts.append(" ".join(article_parts))

    if not prefix_parts:
        return content
    return f"{' - '.join(prefix_parts)}: {content}"


class ClauseChunker:
    """Chunking theo đơn vị điều khoản (Khoản).

    Mỗi clause trong file JSON trở thành một Document, trừ các khoản quá dài
    được tách tiếp theo điểm hoặc sliding window.
    """

    @property
    def strategy_name(self) -> str:
        return "clause"

    def chunk(self, raw_data: Dict[str, Any]) -> List[Document]:
        """Tách từng clause thành một hoặc nhiều Document.

        Args:
            raw_data: Dữ liệu JSON chứa 'law_info' và 'clauses'.

        Returns:
            Danh sách Document với metadata gồm id, law_id, category,
            chunk_part.
        """
        law_info = raw_data.get("law_info", {})
        law_id = law_info.get("law_id")
        law_name = law_info.get("law_name", "")
        category = determine_category(law_name)

        documents = []
        for clause in raw_data.get("clauses", []):
            content = clause.get("content", "")
            if not content.strip():
                continue

            parts = split_long_clause(content)
            is_split = len(parts) > 1
            position = clause.get("position") or {}

            for part_index, part in enumerate(parts):
                metadata = {
                    "id": clause["id"],
                    "law_id": law_id,
                    "category": category,
                    "chunk_part": part_index if is_split else None,
                }
                documents.append(
                    Document(
                        page_content=_build_embedding_content(
                            law_name, position, part
                        ),
                        metadata=metadata,
                    )
                )

        logger.info(
            "Chunked '%s' → %d documents (strategy: clause)",
            law_name[:50], len(documents)
        )
        return documents
