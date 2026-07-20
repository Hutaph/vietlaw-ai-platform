import os

import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LOCAL_MODEL_TESTS") != "1",
    reason="real local model tests are opt-in with RUN_LOCAL_MODEL_TESTS=1",
)


def test_real_embedding_loads_offline():
    from app.services.embedding.hf_endpoint import HuggingFaceEndpointEmbedding

    path = os.getenv(
        "TEST_EMBEDDING_MODEL",
        "../models/embedding/vietlaw-bge-m3-finetuned/best",
    )
    embedding = HuggingFaceEndpointEmbedding(
        model=path,
        mode="local",
        device="cpu",
        expected_dimension=1024,
        local_files_only=True,
    )

    vector = embedding.embed_query("Điều kiện chuyển nhượng quyền sử dụng đất là gì?")

    assert len(vector) == 1024
    assert all(value == value for value in vector)


@pytest.mark.parametrize(
    "env_name,default_path",
    [
        (
            "TEST_RERANKER_CANDIDATE_002_001",
            "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-002-001",
        ),
        (
            "TEST_RERANKER_CANDIDATE_003_004",
            "../models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/candidates/candidate-003-004",
        ),
    ],
)
def test_real_reranker_candidate_loads_offline(env_name, default_path):
    from langchain_core.documents import Document

    from app.services.reranking.cross_encoder import CrossEncoderReranker

    reranker = CrossEncoderReranker(
        model=os.getenv(env_name, default_path),
        device="cpu",
        batch_size=2,
        max_length=512,
        local_files_only=True,
    )

    docs = [
        Document(page_content="Người sử dụng đất được thực hiện quyền chuyển nhượng khi có Giấy chứng nhận và đất không có tranh chấp."),
        Document(page_content="Luật này quy định về hoạt động bảo vệ môi trường và quản lý chất thải."),
    ]
    result = reranker.rerank("Điều kiện chuyển nhượng quyền sử dụng đất là gì?", docs, top_k=2)

    assert len(result) == 2
    assert all("rerank_score" in doc.metadata for doc in result)
