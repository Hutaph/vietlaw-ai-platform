# Design: Fix Streaming Endpoint Desync

## 1. System Architecture
The overall architecture remains the same Client-Server (Next.js + FastAPI) setup, but we are fixing the data flow inside the `/chat/stream` API endpoint and the Frontend `ChatInterface`.

**New Stream Flow:**
1. Frontend sends Query + History to `/chat/stream`.
2. Backend generates `recent_history_str`.
3. Backend calls `Rewriter(last_message, recent_history_str)`.
4. Backend embeds the rewritten query and checks the Semantic Cache.
5. If Cache Hit:
   - Backend yields `{"type": "context", "data": cached_context}` via SSE.
   - Backend loops through the cached text (e.g., splitting by word or fixed chunk size) and yields `{"type": "token", "text": chunk}` to simulate real-time typing.
6. If Cache Miss:
   - Backend calls `aretrieve(rewritten_query)`.
   - Backend yields the full retrieved context.
   - Backend streams LLM tokens.
   - Upon stream completion, Backend calls `update_cache()`.
7. Frontend reads the stream, and continuously parses `<cite id="...">` using Regex to immediately filter the `streamingContext` state variable.

## 2. Component Design

### 2.1 Backend: `backend/app/api/chat.py`
The `chat_stream_endpoint` logic will be updated:
- Introduce `recent_history_str` construction (same logic as `chat_endpoint`, extracting the last 4 messages).
- Modify the rewrite block: `domain, queries = await asyncio.to_thread(pipeline.rewriter.rewrite, last_message, recent_history_str)`
- Add semantic cache check using `query_vector = await asyncio.to_thread(embedding.embed_query, rewritten_query)` and `check_cache`.
- If cache hit: `yield _sse` for context, then loop over words in `cached_response["response_text"]`, sleep slightly (e.g. 0.05s) and `yield _sse({"type": "token", "text": word + " "})`.
- If cache miss: process `aretrieve`, yield context, stream `astream`, accumulate text, then run `update_cache` at the very end.

### 2.2 Frontend: `frontend/components/chat/ChatInterface.tsx`
The streaming reader logic in `handleSubmit` will be updated:
- Store the incoming context into a temporary variable `fullContext`.
- When receiving `event.type === 'token'`, append it to `accumulated`.
- Parse citations: `const citedIds = Array.from(accumulated.matchAll(/<cite\s+id=["']([^"']+)["']>/g)).map(m => m[1]);`
- If `citedIds.length > 0`, filter `fullContext` using those IDs, and call `setStreamingContext(filteredContext)`. Otherwise, keep `streamingContext` as `fullContext` (which means all context is shown initially before any citation is made).

## 3. Data Model
No changes to database schema or Qdrant collections. We continue to use the `semantic_cache` collection.

## 4. API / Interface Changes
No changes to the external REST API signatures. Both `/api/chat/route.ts` and `/chat/stream` will accept and return the same JSON and SSE payload formats. The only change is internal behavior and context payload filtering dynamically.

## 5. Security & Performance
- **Performance**: Semantic cache hit will drop response latency from ~5-10s to <1s.
- Simulated streaming prevents frontend timeouts and preserves UX.
- Client-side filtering is fast as the number of retrieved contexts is small (k=6).
