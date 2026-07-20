# Tasks: Fix Streaming Endpoint Desync

## Phase 1: Backend Updates (Streaming Endpoint)
- [x] 1. Open `backend/app/api/chat.py`.
- [x] 2. In `chat_stream_endpoint`, construct `recent_history_str` from the last 4 messages.
- [x] 3. Call `domain, queries = await asyncio.to_thread(pipeline.rewriter.rewrite, last_message, recent_history_str)`.
- [x] 4. Check Semantic Cache: generate embedding for rewritten query and call `check_cache`.
- [x] 5. Implement Cache Hit logic: if cached, yield the context, loop through `cached_response["response_text"]` splitting by space to yield simulated tokens, and return without invoking the LLM.
- [x] 6. Implement Cache Miss logic: call `aretrieve` with rewritten query, yield the context, then loop over `rag_chain.astream` to yield tokens while accumulating text.
- [x] 7. In Cache Miss logic, call `update_cache` with the accumulated text at the very end of the stream.

## Phase 2: Frontend Updates (Client-side Citation Filtering)
- [x] 8. Open `frontend/components/chat/ChatInterface.tsx`.
- [x] 9. Inside the stream reading loop `while (true) { ... }`, modify the handling of the `context` event to store `fullContext` in a local variable, and update `streamingContext`.
- [x] 10. In the handling of the `token` event, after appending text to `accumulated`, parse citations using `const citedIds = Array.from(accumulated.matchAll(/<cite\s+id=["']([^"']+)["']>/g)).map(m => m[1]);`
- [x] 11. If `citedIds` has elements, filter `fullContext` to only keep those IDs and `setStreamingContext(filteredContext)`.
- [x] 12. Ensure `contextUsed` array passed into `addMessage` on stream end is the correctly filtered context.

## Phase 3: Testing and Validation
- [x] 13. Run a query that requires query rewriting (e.g. asking a follow-up question with pronouns) and observe if the correct laws are retrieved in the stream.
- [x] 14. Run the exact same query again and verify if the semantic cache intercepts the request and streams the cached response quickly without calling the LLM.
- [x] 15. Verify that as the LLM stream types out `<cite id="...">`, the context drawer on the frontend dynamically updates to only show the cited laws.
