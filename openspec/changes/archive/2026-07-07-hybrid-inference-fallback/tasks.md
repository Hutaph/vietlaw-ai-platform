## 1. Environment & Configuration

- [x] 1.1 Update `backend/.env` (and `.env.example`) to include `INFERENCE_STRATEGY=remote_first` or `local_first`.
- [x] 1.2 Update `backend/app/config.py` to load the `INFERENCE_STRATEGY` environment variable.

## 2. LLM Fallback (Rewriting & Generation)

- [x] 2.1 Refactor `backend/app/services/llm.py` to instantiate both a remote LLM (HuggingFace/OpenAI) and a local LLM (Ollama).
- [x] 2.2 Wrap the primary LLM with the secondary LLM using `with_fallbacks()` from Langchain based on `INFERENCE_STRATEGY`.

## 3. Embedding Fallback

- [x] 3.1 Create `InferenceFallbackManager` (or similar logic) in `backend/app/services/embedding/__init__.py`.
- [x] 3.2 Implement a generic `embed_documents` / `embed_query` try-catch block to try `PrimaryEmbedding` and fallback to `SecondaryEmbedding` upon failure.

## 4. Reranking Fallback

- [x] 4.1 Create fallback logic in `backend/app/services/reranking/__init__.py` to handle reranking failures.
- [x] 4.2 Allow `NoReranker` to act as a fallback for `CrossEncoderReranker` if the local cross-encoder runs out of memory or crashes.

## 5. Pipeline Integration & Testing

- [x] 5.1 Ensure `backend/app/services/pipeline.py` correctly requests the wrapper models (LLM, Embeddings, Reranker).
- [x] 5.2 Validate that when the primary LLM API throws a deliberate Exception, the fallback seamlessly completes the RAG workflow.
- [x] 5.3 Implement error handling to throw a 503/500 HTTP response if BOTH primary and fallback models fail.
