## Context

Our RAG system directly searches Qdrant using the user's raw input. Users often use everyday slang or vague questions ("sổ đỏ", "làm giấy tờ xe") rather than formal legal terminology. This causes a semantic mismatch, reducing the effectiveness of both dense and sparse vector search. We need an intelligent way to translate and break down user queries before hitting the database.

## Goals / Non-Goals

**Goals:**
- Implement an LLM-based `QueryRewriter` to classify intent and translate legal slang to formal terms.
- Use a rigid JSON structure for the LLM output to allow deterministic parsing.
- Support Multi-Query retrieval (sending the original query + rewritten queries to Qdrant) for maximum recall.
- Route non-legal questions (chitchat) around Qdrant entirely to save costs and time.

**Non-Goals:**
- We are not replacing the main LLM answer generation model; the rewriter is a secondary, smaller utility model.
- We will not rewrite every single message (e.g., simple conversational acknowledgments like "Cảm ơn").

## Decisions

1. **LLM Structured Output (JSON)**:
   - The rewriter must output JSON in the format: `{"domain": "legal"|"chitchat", "queries": ["query1", "query2"]}`. This ensures we can easily extract the routing decision and the search strings.

2. **Multi-Query Architecture**:
   - Instead of replacing the user query, we will send an array of queries to Qdrant (e.g., the original query + the legal translation). The results from all queries will be pooled together, deduplicated by `law_id` + `clause_id`, and then scored by the Cross-Encoder Reranker.

3. **Modular Integration**:
   - The `QueryRewriter` will be added to `backend/app/services/pipeline.py` and can be configured via `.env` (`PIPELINE_REWRITER=llm` vs `none`) so it can be disabled if latency is an issue.

## Risks / Trade-offs

- **[Risk] Latency Increase** → Calling an LLM before retrieval adds overhead.
  - *Mitigation*: We recommend using a small, extremely fast model (like Qwen2.5-1.5B or Llama-3.2-1B) specifically for this rewriting task, either locally via Ollama or via a very fast API endpoint.
- **[Risk] LLM JSON parsing failures** → LLMs might not always output perfect JSON.
  - *Mitigation*: We will use Langchain's robust JSON parsing utilities and implement a fallback: if JSON parsing fails, the system defaults to routing as "legal" and uses the raw user query.
