## 1. Update Rewriter Interface

- [x] 1.1 Update `BaseRewriter.rewrite` method in `backend/app/services/rewriting/base.py` to accept an optional `history: str = None` parameter.

## 2. Update LLMRewriter Implementation

- [x] 2.1 Update `LLMRewriter.rewrite` method in `backend/app/services/rewriting/llm_rewriter.py` to accept the `history` parameter.
- [x] 2.2 Modify `LLMRewriter.prompt` to include `{history}` as part of the context for the model. Update the instructions so the model uses the history to resolve pronouns and implicit references in the current query.
- [x] 2.3 Pass `history` to `self.chain.invoke` in the `LLMRewriter.rewrite` method.

## 3. Inject History from Chat Endpoint

- [x] 3.1 In `backend/app/api/chat.py` endpoint `/chat`, extract the last 2 conversation turns (up to 4 messages) from `request.messages[:-1]`.
- [x] 3.2 Format the extracted turns into a `recent_history_str`.
- [x] 3.3 Pass `recent_history_str` to `pipeline.rewriter.rewrite`.

## 4. Testing & Validation

- [x] 4.1 Test the RAG pipeline with a contextual follow-up query (e.g., "Mức phạt là bao nhiêu?") after a context-setting query.
- [x] 4.2 Verify that the semantic cache saves the contextually-resolved rewritten query and hits the cache on identical follow-up queries.
