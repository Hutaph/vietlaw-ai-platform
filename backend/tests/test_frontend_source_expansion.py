from langchain_core.documents import Document

from app.services.context_builder.nested_context import NestedContextBuilder
from app.services.knowledge_base import KNOWLEDGE_BASE, LAW_METADATA


def test_frontend_sources_expand_to_full_article_context():
    KNOWLEDGE_BASE.clear()
    LAW_METADATA.clear()
    LAW_METADATA["LCCONGCHUNG_VBHN"] = {"law_name": "Luật Công chứng", "summary": ""}
    KNOWLEDGE_BASE.update(
        {
            "LCCONGCHUNG_VBHN_D67": {
                "law_id": "LCCONGCHUNG_VBHN",
                "position": {"article": "67", "article_title": "Hồ sơ công chứng", "order_index": 1},
                "content": "Điều 67. Hồ sơ công chứng",
            },
            "LCCONGCHUNG_VBHN_D67_K1": {
                "law_id": "LCCONGCHUNG_VBHN",
                "position": {"article": "67", "article_title": "Hồ sơ công chứng", "clause": "1", "order_index": 2},
                "content": "1. Phiếu yêu cầu công chứng.",
            },
            "LCCONGCHUNG_VBHN_D67_K2": {
                "law_id": "LCCONGCHUNG_VBHN",
                "position": {"article": "67", "article_title": "Hồ sơ công chứng", "clause": "2", "order_index": 3},
                "content": "2. Dự thảo hợp đồng, giao dịch.",
            },
        }
    )

    result = NestedContextBuilder().format_for_frontend(
        [Document(page_content="Điều 67. Hồ sơ công chứng", metadata={"id": "LCCONGCHUNG_VBHN_D67"})]
    )

    assert result[0]["metadata"]["id"] == "LCCONGCHUNG_VBHN_D67"
    assert "Điều 67. Hồ sơ công chứng" in result[0]["content"]
    assert "1. Phiếu yêu cầu công chứng." in result[0]["content"]
    assert "2. Dự thảo hợp đồng, giao dịch." in result[0]["content"]
