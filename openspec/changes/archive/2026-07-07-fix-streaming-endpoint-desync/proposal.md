# Proposal: Fix Streaming Endpoint Desync

## 1. Context and Problem
The project recently implemented advanced capabilities in the backend, including **Query Rewriting Memory** (for resolving conversation history anaphora), **Semantic Caching** (to return exact responses for similar queries instantly), and **Strict Citation Filtering** (to omit retrieved context that the LLM did not actually cite). 

However, these features were exclusively implemented in the non-streaming `/chat` endpoint. The frontend UI currently uses the `/api/chat/route.ts` proxy, which connects directly to the `/chat/stream` endpoint. Because of this architectural desynchronization, real users on the frontend are completely bypassed from all these new advanced features. The streaming endpoint simply takes the query, performs standard retrieval without conversational history, and streams the LLM response.

## 2. Proposed Solution
We need to synchronize the feature set of `/chat/stream` with the main `/chat` endpoint, but adapt the approach to fit the Server-Sent Events (SSE) paradigm:
1. **Query Rewriting Memory**: Pass the `recent_history_str` into the rewriter within the streaming endpoint before calling `aretrieve`.
2. **Semantic Caching**: Generate an embedding for the rewritten query and check the Qdrant semantic cache *before* calling the LLM. If there is a cache hit, stream the cached text back to the frontend chunk by chunk to maintain a seamless UX, and bypass the LLM entirely.
3. **Client-side Citation Filtering**: Because the streaming endpoint must send the retrieved context to the frontend immediately (before the LLM generates tokens), it cannot filter the context on the backend. We will shift the citation parsing responsibility to the frontend: `ChatInterface.tsx` will parse `<cite id="...">` tags from the incoming stream in real-time, and dynamically filter or highlight the context drawer items that the LLM references.

## 3. Scope
- Update `backend/app/api/chat.py` (`chat_stream_endpoint`) to include rewriting history and semantic caching check/update logic.
- Update `frontend/components/chat/ChatInterface.tsx` to handle dynamic citation parsing and filtering during streaming.

## 4. Non-Goals
- We are not replacing or changing the underlying Qdrant, PostgreSQL, or BM25 implementation.
- We are not changing the LLM prompts or the core `RAGPipeline` component.
