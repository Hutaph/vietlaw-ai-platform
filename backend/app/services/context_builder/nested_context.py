"""
Nested Context Builder.
Default strategy that preserves the legacy two-level reference expansion.
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from app.services.knowledge_base import (
    KNOWLEDGE_BASE, LAW_METADATA,
    resolve_reference_data,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.context_builder.nested")

FRONTEND_SOURCE_MAX_CHARS = 5000


class NestedContextBuilder:
    """Build two-level context with legal cross-reference resolution.

    Level 1: full content of directly referenced clauses.
    Level 2: summary text for second-order references.

    This suits Vietnamese legal documents where clauses often reference each
    other.
    """

    @property
    def strategy_name(self) -> str:
        return "nested_2_level"

    def _clause_from_document(self, doc: Document) -> Dict[str, Any]:
        """Return clause data from memory or fall back to Qdrant payload metadata."""
        metadata = doc.metadata or {}
        clause_id = metadata.get("id")
        clause_data = KNOWLEDGE_BASE.get(clause_id)
        if clause_data:
            return clause_data

        position = metadata.get("position") or {}
        if not isinstance(position, dict):
            position = {}

        law_id = metadata.get("law_id") or metadata.get("source") or metadata.get("law") or ""
        law_name = (
            metadata.get("law_name")
            or metadata.get("source")
            or metadata.get("law")
            or law_id
            or "Văn bản pháp luật"
        )

        return {
            "law_id": law_id,
            "position": position,
            "content": doc.page_content or "",
            "cross_references": [],
            "_fallback_law_name": law_name,
        }

    def _law_name(self, clause_data: Dict[str, Any]) -> str:
        law_id = clause_data.get("law_id")
        law_meta = LAW_METADATA.get(law_id, {}) if law_id else {}
        return law_meta.get("law_name") or clause_data.get("_fallback_law_name") or law_id or "Văn bản pháp luật"

    def _article_clauses(self, clause_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return all in-memory chunks that belong to the same legal article."""
        law_id = clause_data.get("law_id")
        position = clause_data.get("position", {})
        article = position.get("article") if isinstance(position, dict) else None
        if not law_id or article in (None, ""):
            return [clause_data]

        matches = []
        for candidate in KNOWLEDGE_BASE.values():
            candidate_pos = candidate.get("position", {})
            if not isinstance(candidate_pos, dict):
                continue
            if candidate.get("law_id") == law_id and candidate_pos.get("article") == article:
                matches.append(candidate)

        if not matches:
            return [clause_data]

        def sort_order(value: Any) -> int:
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0

        def sort_key(candidate: Dict[str, Any]) -> tuple:
            pos = candidate.get("position", {})
            return (
                sort_order(pos.get("order_index")),
                str(pos.get("clause") or ""),
                str(pos.get("point") or ""),
                str(candidate.get("content") or ""),
            )

        return sorted(matches, key=sort_key)

    def _format_frontend_content(self, clause_data: Dict[str, Any]) -> str:
        """Build reader-friendly source text with enough surrounding article context."""
        article_clauses = self._article_clauses(clause_data)
        if len(article_clauses) <= 1:
            return clause_data.get("content", "")

        pos = clause_data.get("position", {})
        article = pos.get("article", "")
        article_title = pos.get("article_title", "")
        heading = f"Điều {article}. {article_title}".strip()
        if not article:
            heading = article_title or "Nội dung điều luật"

        lines = [heading]
        seen = set()
        for item in article_clauses:
            content = str(item.get("content") or "").strip()
            if not content or content in seen:
                continue
            seen.add(content)
            if content == heading or content.startswith(f"{heading}\n"):
                continue
            lines.append(content)

        expanded = "\n\n".join(lines).strip()
        if len(expanded) <= FRONTEND_SOURCE_MAX_CHARS:
            return expanded
        return f"{expanded[:FRONTEND_SOURCE_MAX_CHARS].rstrip()}..."

    def build(self, documents: List[Document]) -> str:
        """Build a two-level recursive legal context string."""
        context_blocks = []
        used_law_ids = set()

        for i, doc in enumerate(documents):
            clause_id = doc.metadata.get("id")
            clause_data = self._clause_from_document(doc)
            if not clause_data.get("content"):
                continue

            law_id = clause_data.get("law_id")
            if law_id:
                used_law_ids.add(law_id)

            pos = clause_data.get("position", {})
            law_name = self._law_name(clause_data)

            chapter_val = pos.get('chapter', '')
            chapter_title = pos.get('chapter_title', '')
            article_val = pos.get('article', '')
            article_title = pos.get('article_title', '')
            clause_val = pos.get('clause', '')

            chapter_str = f"Chương {chapter_val} ({chapter_title})" if chapter_title else f"Chương {chapter_val}"
            article_str = f"Điều {article_val} ({article_title})" if article_title else f"Điều {article_val}"

            # [0] Main legal basis.
            block = f"[CĂN CỨ ID: {clause_id}]\n"
            block += f"- Nguồn: {law_name} | {chapter_str} | {article_str} | Khoản {clause_val}\n"
            block += f"- Nội dung: \"{clause_data['content']}\"\n"

            refs_level_1 = clause_data.get("cross_references", [])
            if refs_level_1:
                block += "   >> DẪN CHIẾU BỔ SUNG:\n"

                for ref1 in refs_level_1:
                    target_id_1 = ref1.get("target_id", "")
                    anchor_text_1 = ref1.get("anchor_text", target_id_1)

                    # Resolve level-1 reference data.
                    resolved_clauses_1 = resolve_reference_data(target_id_1)

                    if resolved_clauses_1:
                        # [1] Level-1 reference with full content.
                        content_1 = " ".join([c["content"] for c in resolved_clauses_1])
                        target_law_id_1 = resolved_clauses_1[0]["law_id"]
                        target_law_name_1 = LAW_METADATA[target_law_id_1]["law_name"]
                        used_law_ids.add(target_law_id_1)

                        block += f"   + [Cấp 1] Tại cụm từ '{anchor_text_1}' ({target_law_name_1}):\n"
                        block += f"     Nội dung: \"{content_1}\"\n"

                        # [2] Level-2 references with summaries only.
                        refs_level_2 = []
                        for c in resolved_clauses_1:
                            refs_level_2.extend(c.get("cross_references", []))

                        # Deduplicate and avoid references that point back to the source.
                        seen_targets = set()
                        unique_refs_level_2 = []
                        for r2 in refs_level_2:
                            t2_id = r2.get("target_id")
                            if t2_id not in seen_targets and t2_id != target_id_1 and t2_id != clause_id:
                                seen_targets.add(t2_id)
                                unique_refs_level_2.append(r2)

                        if unique_refs_level_2:
                            for ref2 in unique_refs_level_2:
                                anchor_text_2 = ref2.get("anchor_text", ref2.get("target_id", ""))
                                summary_text_2 = ref2.get("description_summary") or ref2.get("description", "Vui lòng xem chi tiết tại văn bản gốc.")

                                block += f"       -> [Cấp 2] Có liên quan đến '{anchor_text_2}': (Tóm tắt) {summary_text_2}\n"

                    else:
                        # Fallback when the reference cannot be resolved in memory.
                        summary_text_1 = ref1.get("description_summary") or ref1.get("description", "")
                        block += f"   + [Cấp 1] Tại cụm từ '{anchor_text_1}': (Tóm tắt) {summary_text_1}\n"

            context_blocks.append(block)

        # Add a header that summarizes all source laws used in this context.
        header = "--- THÔNG TIN CÁC VĂN BẢN ĐƯỢC SỬ DỤNG ---\n"
        for l_id in used_law_ids:
            meta = LAW_METADATA.get(l_id)
            if meta:
                header += f"- {meta['law_name']}: {meta['summary']}\n"
        header += "\n--- CHI TIẾT CĂN CỨ VÀ DẪN CHIẾU ---\n"

        return header + "\n\n".join(context_blocks)

    def build_compact(self, documents: List[Document]) -> str:
        """Build a compact context that preserves source IDs, legal metadata, and main text."""
        context_blocks = []
        used_law_ids = set()

        for doc in documents:
            clause_id = doc.metadata.get("id")
            clause_data = self._clause_from_document(doc)
            if not clause_data.get("content"):
                continue

            law_id = clause_data.get("law_id")
            if law_id:
                used_law_ids.add(law_id)
            pos = clause_data.get("position", {})
            law_name = self._law_name(clause_data)
            article_val = pos.get("article", "")
            article_title = pos.get("article_title", "")
            clause_val = pos.get("clause", "")

            block = f"[CĂN CỨ ID: {clause_id}]\n"
            block += f"- Văn bản: {law_name}\n"
            block += f"- Điều: {article_val}\n"
            if clause_val != "":
                block += f"- Khoản: {clause_val}\n"
            if article_title:
                block += f"- Tiêu đề: {article_title}\n"
            block += f"- Nội dung: \"{clause_data['content']}\"\n"
            context_blocks.append(block)

        header = "--- THÔNG TIN CÁC VĂN BẢN ĐƯỢC SỬ DỤNG ---\n"
        for law_id in used_law_ids:
            meta = LAW_METADATA.get(law_id)
            if meta:
                header += f"- {meta['law_name']}: {meta['summary']}\n"
        header += "\n--- CHI TIẾT CĂN CỨ ---\n"
        return header + "\n\n".join(context_blocks)

    def format_for_frontend(self, documents: List[Document]) -> List[Dict[str, Any]]:
        """Format retrieved documents for frontend display."""
        formatted = []
        for doc in documents:
            c_id = doc.metadata.get("id")
            data = self._clause_from_document(doc)
            if not data.get("content"):
                continue

            pos = data.get("position", {})
            law_name = self._law_name(data)

            formatted.append({
                "content": self._format_frontend_content(data),
                "metadata": {
                    "id": c_id,
                    "source": law_name,
                    "dieu": pos.get("article"),
                    "khoan": pos.get("clause"),
                    "title": pos.get("article_title"),
                    "expanded": True,
                    "law": law_name
                }
            })
        return formatted
