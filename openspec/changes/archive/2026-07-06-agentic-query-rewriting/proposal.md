## Why

Users often use slang, everyday terminology, or non-legal language (e.g., "sổ đỏ") when asking legal questions, which creates a semantic mismatch with the formal language used in legal documents (e.g., "giấy chứng nhận quyền sử dụng đất"). By introducing an Agentic Query Rewriter before the retrieval step, we can translate user intents into precise legal terms and decompose complex queries into multiple sub-queries. This will maximize retrieval recall and precision. Additionally, an intelligent agent can act as a Router, instantly short-circuiting non-legal queries (chitchat) to save heavy Qdrant search and LLM context generation costs.

## What Changes

- Introduce a new `QueryRewriter` module that leverages a small LLM (local or API-based) to act as an intelligent pre-processor.
- Implement a rigid JSON schema enforcement for the Rewriter to output routing decisions (`legal` vs `chitchat`) and multiple search queries.
- Update the retrieval pipeline to perform Multi-Query search and deduplicate results before passing them to the Cross-Encoder Reranker.
- Add configuration toggles to enable/disable the Rewriter for ablation studies and testing.

## Capabilities

### New Capabilities
- `query-rewriting`: Capability for parsing user inputs, classifying domains, translating slang to formal legal terms, and generating multiple sub-queries.

### Modified Capabilities
- `retrieval-persistence`: Modify the retrieval pipeline to support handling an array of queries instead of a single string, applying deduplication to the pooled results before reranking.

## Impact

- **Search Pipeline**: Modifies `backend/app/services/pipeline.py` to intercept user queries before Qdrant retrieval.
- **Latency**: Will introduce a slight delay (2-4s) before results are retrieved, which should be offset by using a fast/small LLM specifically for rewriting.
- **Dependencies**: May require structural changes to how prompts are sent for small utility tasks vs large generation tasks.
