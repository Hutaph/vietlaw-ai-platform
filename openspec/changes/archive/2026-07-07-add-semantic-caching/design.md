## Context

The Vietnam Legal QA System currently executes the full Agentic RAG pipeline for every user query. This involves query rewriting, vector database search (FAISS/Qdrant), reranking, context building, and finally calling the LLM to generate an answer. Given the legal domain, users frequently ask semantically identical questions (e.g., "Mức phạt vượt đèn đỏ" and "Vượt đèn đỏ bị phạt bao nhiêu tiền"). Executing the entire pipeline for these queries is redundant, slow, and expensive in terms of LLM usage.

## Goals / Non-Goals

**Goals:**
- Decrease latency significantly (from seconds to milliseconds) for frequently asked questions.
- Reduce LLM API costs by bypassing the generation step for cached queries.
- Ensure the frontend receives the correct citation metadata (`contextUsed`) from the cache, just as it would from a live generation.
- Implement without adding massive new infrastructure dependencies (like Redis, if possible).

**Non-Goals:**
- Caching entire conversational histories (we only care about the standalone, rewritten query).
- Complex, granular cache invalidation strategies (e.g., event-driven invalidation from specific legal updates in real-time) for this initial phase.

## Decisions

1. **Storage Backend: Reuse Qdrant**
   - *Rationale*: While Redis (with RedisVL) is traditionally used for caching, Qdrant is already running in the `docker-compose.yml` for our document storage. Reusing it by creating a dedicated `semantic_cache` collection avoids adding a new service, keeping the memory footprint and operational complexity low.
   - *Alternative*: Redis. Rejected to minimize infrastructure bloat.

2. **What to Embed and Match**
   - *Rationale*: We will generate the embedding based on the **Rewritten Query** (which resolves conversational context into a standalone legal question) rather than the raw user input. This dramatically increases the cache hit rate.

3. **Cache Structure**
   - *Rationale*: The `semantic_cache` Qdrant collection will store vectors (representing the rewritten query). The payload will contain:
     - `original_query`
     - `response_text`: The LLM's generated response
     - `context_used`: The JSON-serialized array of documents cited (for strict citation UI support)
     - `timestamp`: When it was cached

4. **Cache Hit Threshold**
   - *Rationale*: Set a high cosine similarity threshold (e.g., `0.95` or `0.96`, configurable via `.env`) to avoid false positives. Law is precise; a slightly different query might require a very different legal answer.

## Risks / Trade-offs

- **[Risk] Outdated Information**: Laws change, and a cached answer from 6 months ago might be invalid today.
  - *Mitigation*: Implement a Time-To-Live (TTL) or periodic cleanup mechanism for the cache collection (e.g., clear cache every 30 days). Also, provide a management script (`scripts/clear_cache.py`) to manually flush the cache when the knowledge base is updated.
- **[Risk] False Positives**: Answering a nuanced query with a generic cached response because the similarity score barely crossed the threshold.
  - *Mitigation*: Start with a very strict similarity threshold and monitor cache hits vs. misses. Allow it to be configurable via `SEMANTIC_CACHE_THRESHOLD`.
