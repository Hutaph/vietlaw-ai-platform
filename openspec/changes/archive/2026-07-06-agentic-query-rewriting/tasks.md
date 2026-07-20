## 1. Setup & Configuration

- [x] 1.1 Add `PIPELINE_REWRITER`, `REWRITER_MODEL_PROVIDER`, and `REWRITER_MODEL_NAME` to `backend/.env.example` and config loaders.
- [x] 1.2 Create `backend/app/services/rewriting/` module directory structure.

## 2. Implement QueryRewriter

- [x] 2.1 Define `BaseRewriter` interface in `backend/app/services/rewriting/base.py`.
- [x] 2.2 Implement `NoOpRewriter` that just returns `("legal", [original_query])` for backward compatibility.
- [x] 2.3 Implement `LLMRewriter` using Langchain's JSON parser, implementing the system prompt for classifying and rewriting legal terminology.
- [x] 2.4 Add robust JSON fallback mechanism in `LLMRewriter` to handle parsing failures gracefully.

## 3. Update Pipeline & Retrieval

- [x] 3.1 Update `QdrantSearcher` to accept a list of queries (multi-query) and perform a multi-prefetch approach or loop through queries.
- [x] 3.2 Update `RAGPipeline` to initialize the selected rewriter based on environment variables.
- [x] 3.3 Update `RAGPipeline.retrieve()` to execute the rewriter first.
- [x] 3.4 Implement chitchat routing: if domain is "chitchat", return early with an empty document list.
- [x] 3.5 Implement deduplication logic for pooled Qdrant results before passing them to the Cross-Encoder Reranker.

## 4. Testing & Validation

- [x] 4.1 Write a test script `backend/test_rewriter.py` to test the JSON output format on complex slang questions (e.g. "sổ đỏ", "đất tranh chấp").
- [x] 4.2 Verify that end-to-end multi-query search successfully fuses and reranks results accurately.
