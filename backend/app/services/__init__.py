# Business logic services package
#
# Module architecture (for ablation study):
#   embedding/       → Text embedding strategies
#   chunking/        → Document chunking strategies
#   search/          → Search/retrieval strategies (FAISS, BM25, Hybrid)
#   reranking/       → Reranking strategies (None, Cross-encoder)
#   context_builder/ → Context building strategies
#   pipeline.py      → Orchestrator that composes the above modules
#   knowledge_base.py → In-memory knowledge base
#   llm.py           → LLM connection and prompts
