"""
Legacy RAG helpers for retrieval and context building.
Kept for compatibility with older code paths.
"""
from typing import List, Dict, Any

from langchain_core.documents import Document

from app.config import RETRIEVER_K, RETRIEVER_FETCH_K, RETRIEVER_LAMBDA_MULT
from app.services.vectorstore import (
    get_vectorstore,
    KNOWLEDGE_BASE, LAW_METADATA,
)
from app.services.knowledge_base import (
    ALL_LAWS_CATEGORY,
    document_matches_category,
    normalize_category,
)


def resolve_reference_data(target_id: str) -> List[Dict[str, Any]]:
    """Resolve an exact clause or collect all clauses under an article."""
    if target_id in KNOWLEDGE_BASE:
        return [KNOWLEDGE_BASE[target_id]]

    results = []
    search_prefix = f"{target_id}_"
    for k, v in KNOWLEDGE_BASE.items():
        if k.startswith(search_prefix):
            results.append(v)
    return results


def get_retriever(category: str = ALL_LAWS_CATEGORY) -> Any:
    """Create a retriever for relevant legal text chunks."""
    vectorstore = get_vectorstore()

    search_kwargs = {
        "k": RETRIEVER_K,
        "fetch_k": RETRIEVER_FETCH_K,
        "lambda_mult": RETRIEVER_LAMBDA_MULT,
    }

    # Apply a legal category filter when requested.
    normalized_category = normalize_category(category)
    if normalized_category != ALL_LAWS_CATEGORY:
        search_kwargs["filter"] = (
            lambda metadata: document_matches_category(
                metadata,
                normalized_category,
            )
        )

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs=search_kwargs
    )


def build_nested_context(retrieved_docs: List[Document]) -> str:
    """Build a two-level context string with direct content and summaries."""
    context_blocks = []
    used_law_ids = set()

    for i, doc in enumerate(retrieved_docs):
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

                    # Deduplicate and avoid references pointing back to the source.
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
                    # Fallback when the referenced law cannot be resolved in memory.
                    summary_text_1 = ref1.get("description_summary") or ref1.get("description", "")
                    block += f"   + [Cấp 1] Tại cụm từ '{anchor_text_1}': (Tóm tắt) {summary_text_1}\n"

        context_blocks.append(block)

    # Add a header summarizing all source laws used in this context.
    header = "--- THÔNG TIN CÁC VĂN BẢN ĐƯỢC SỬ DỤNG ---\n"
    for l_id in used_law_ids:
        meta = LAW_METADATA.get(l_id)
        if meta:
            header += f"- {meta['law_name']}: {meta['summary']}\n"
    header += "\n--- CHI TIẾT CĂN CỨ VÀ DẪN CHIẾU ---\n"

    return header + "\n\n".join(context_blocks)


def format_docs_for_frontend(docs: List[Document]) -> List[Dict[str, Any]]:
    """Format retrieved documents for frontend display."""
    formatted = []
    for doc in docs:
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
