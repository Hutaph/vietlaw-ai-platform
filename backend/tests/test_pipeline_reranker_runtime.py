from langchain_core.documents import Document

from app.services.pipeline import RAGPipeline


class _NoOpRewriter:
    def rewrite(self, query):
        return "legal", [query]


class _Searcher:
    strategy_name = "fake"

    def search(self, queries, k, category=None):
        return [Document(page_content="a", metadata={"id": "a"})]


class _Reranker:
    strategy_name = "fake_reranker"

    def __init__(self):
        self.calls = 0

    def rerank(self, query, documents, top_k):
        self.calls += 1
        return documents[:top_k]


class _ContextBuilder:
    strategy_name = "fake_context"

    def build(self, docs):
        return "\n".join(doc.page_content for doc in docs)

    def format_for_frontend(self, docs):
        return []


class _BudgetContextBuilder:
    strategy_name = "budget_context"

    def build(self, docs):
        return "x" * 100

    def build_compact(self, docs):
        return "\n".join(f"[CĂN CỨ ID: {doc.metadata['id']}]\n{doc.page_content}" for doc in docs)

    def format_for_frontend(self, docs):
        return []


def test_request_disable_reranker_does_not_call_inference():
    reranker = _Reranker()
    pipeline = RAGPipeline(
        rewriter=_NoOpRewriter(),
        searcher=_Searcher(),
        reranker=reranker,
        context_builder=_ContextBuilder(),
    )

    docs, context = pipeline.retrieve("q", enable_reranker=False, rerank_top_k=1)

    assert len(docs) == 1
    assert context == "a"
    assert reranker.calls == 0


def test_context_budget_uses_compact_context_to_preserve_final_sources():
    pipeline = RAGPipeline(
        rewriter=_NoOpRewriter(),
        searcher=_Searcher(),
        reranker=_Reranker(),
        context_builder=_BudgetContextBuilder(),
    )
    docs = [
        Document(page_content="nội dung 1", metadata={"id": "A"}),
        Document(page_content="nội dung 2", metadata={"id": "B"}),
    ]

    selected, context = pipeline._build_context_with_budget(docs, token_budget=20)

    assert [doc.metadata["id"] for doc in selected] == ["A", "B"]
    assert "[CĂN CỨ ID: A]" in context
    assert "[CĂN CỨ ID: B]" in context
