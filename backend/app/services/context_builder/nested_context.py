"""
Nested Context Builder — Xây dựng context đệ quy 2 cấp.
Đây là strategy mặc định, giữ nguyên logic từ rag.py cũ.
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from app.services.knowledge_base import (
    KNOWLEDGE_BASE, LAW_METADATA,
    resolve_reference_data,
)
from app.utils.logging import setup_logger

logger = setup_logger("vietlaw.context_builder.nested")


class NestedContextBuilder:
    """Xây dựng context đệ quy 2 cấp với cross-reference resolution.

    Cấp 1: Nội dung đầy đủ của điều khoản được dẫn chiếu
    Cấp 2: Tóm tắt của các dẫn chiếu bậc 2

    Đây là chiến lược tối ưu cho văn bản pháp luật Việt Nam
    vì các điều khoản thường dẫn chiếu chéo lẫn nhau.
    """

    @property
    def strategy_name(self) -> str:
        return "nested_2_level"

    def build(self, documents: List[Document]) -> str:
        """Xây dựng chuỗi ngữ cảnh đệ quy 2 Cấp."""
        context_blocks = []
        used_law_ids = set()

        for i, doc in enumerate(documents):
            clause_id = doc.metadata.get("id")
            clause_data = KNOWLEDGE_BASE.get(clause_id)
            if not clause_data:
                continue

            law_id = clause_data["law_id"]
            used_law_ids.add(law_id)

            pos = clause_data["position"]
            law_name = LAW_METADATA[law_id]["law_name"]

            chapter_val = pos.get('chapter', '')
            chapter_title = pos.get('chapter_title', '')
            article_val = pos.get('article', '')
            article_title = pos.get('article_title', '')
            clause_val = pos.get('clause', '')

            chapter_str = f"Chương {chapter_val} ({chapter_title})" if chapter_title else f"Chương {chapter_val}"
            article_str = f"Điều {article_val} ({article_title})" if article_title else f"Điều {article_val}"

            # [0] CĂN CỨ CHÍNH
            block = f"[CĂN CỨ ID: {clause_id}]\n"
            block += f"- Nguồn: {law_name} | {chapter_str} | {article_str} | Khoản {clause_val}\n"
            block += f"- Nội dung: \"{clause_data['content']}\"\n"

            refs_level_1 = clause_data.get("cross_references", [])
            if refs_level_1:
                block += "   >> DẪN CHIẾU BỔ SUNG:\n"

                for ref1 in refs_level_1:
                    target_id_1 = ref1.get("target_id", "")
                    anchor_text_1 = ref1.get("anchor_text", target_id_1)

                    # Tìm dữ liệu của Cấp 1
                    resolved_clauses_1 = resolve_reference_data(target_id_1)

                    if resolved_clauses_1:
                        # [1] DẪN CHIẾU CẤP 1 (Lấy toàn bộ Content)
                        content_1 = " ".join([c["content"] for c in resolved_clauses_1])
                        target_law_id_1 = resolved_clauses_1[0]["law_id"]
                        target_law_name_1 = LAW_METADATA[target_law_id_1]["law_name"]
                        used_law_ids.add(target_law_id_1)

                        block += f"   + [Cấp 1] Tại cụm từ '{anchor_text_1}' ({target_law_name_1}):\n"
                        block += f"     Nội dung: \"{content_1}\"\n"

                        # [2] DẪN CHIẾU CẤP 2 (Chỉ lấy Tóm tắt)
                        refs_level_2 = []
                        for c in resolved_clauses_1:
                            refs_level_2.extend(c.get("cross_references", []))

                        # Lọc trùng lặp và tránh trỏ ngược về chính nó
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
                        # Fallback nếu không quét được trong RAM
                        summary_text_1 = ref1.get("description_summary") or ref1.get("description", "")
                        block += f"   + [Cấp 1] Tại cụm từ '{anchor_text_1}': (Tóm tắt) {summary_text_1}\n"

            context_blocks.append(block)

        # Tạo phần Header tổng hợp thông tin văn bản
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
            clause_data = KNOWLEDGE_BASE.get(clause_id)
            if not clause_data:
                continue

            law_id = clause_data["law_id"]
            used_law_ids.add(law_id)
            pos = clause_data["position"]
            law_name = LAW_METADATA[law_id]["law_name"]
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
        """Định dạng lại dữ liệu trả về để Frontend dễ dàng hiển thị lên UI."""
        formatted = []
        for doc in documents:
            c_id = doc.metadata.get("id")
            data = KNOWLEDGE_BASE.get(c_id, {})
            if not data:
                continue

            pos = data.get("position", {})
            law_name = LAW_METADATA.get(data.get("law_id"), {}).get("law_name", "")

            formatted.append({
                "content": data.get("content", ""),
                "metadata": {
                    "id": c_id,
                    "source": law_name,
                    "dieu": pos.get("article"),
                    "khoan": pos.get("clause"),
                    "law": law_name
                }
            })
        return formatted
