## Why

Users frequently ask variations of the exact same legal questions (e.g., "Thủ tục đăng ký kinh doanh" vs "Cho mình hỏi cách mở công ty"). Running the full Agentic RAG pipeline (vector search + LLM generation) for semantically identical queries is slow and incurs unnecessary LLM costs. A semantic cache will bypass these expensive steps and drastically reduce latency for repeat queries.

## What Changes

- Introduce a Semantic Caching layer into the RAG pipeline.
- Intercept the workflow *after* query rewriting but *before* vector search and LLM generation.
- Store previously generated answers (along with their `contextUsed` citations) based on the vector embeddings of the standalone rewritten queries.
- Return cached responses instantly when a new query is semantically equivalent to a cached one (e.g., cosine similarity > threshold).
- Utilize the existing Qdrant infrastructure to store the `semantic_cache` collection, avoiding the need for new services like Redis.

## Capabilities

### New Capabilities
- `semantic-caching`: Bypasses the full RAG retrieval and generation pipeline for queries that are semantically similar to previously answered questions, returning cached responses and citations.

### Modified Capabilities
- None.

## Impact

- **API/Endpoints**: `backend/app/api/chat.py` will be updated to orchestrate cache lookups and cache updates.
- **Services**: A new `CacheManager` or integration within `pipeline.py` will be introduced.
- **Storage**: A new `semantic_cache` collection will be created in the existing Qdrant database.
- **Performance**: Drastically improved response times for frequent queries, reduced LLM API usage.
