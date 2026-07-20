## Why

Currently, the Query Rewriting module (`LLMRewriter`) only takes the latest user query into account, disregarding previous conversation history. This causes anaphoric references (e.g., "Vậy mức phạt là bao nhiêu?" referring to a previously mentioned violation) to lose their context, resulting in poor retrieval and semantic cache misses. This change addresses this "amnesia" by integrating conversational memory into the rewriter to produce context-aware, standalone legal queries in a single LLM pass.

## What Changes

- Modify `BaseRewriter` and `LLMRewriter` to accept an optional `history` parameter (sliding window of the last 2-3 chat turns).
- Update the system prompt in `LLMRewriter` to instruct the model to use the conversation history for context resolution when translating to formal legal terms.
- Update `app/api/chat.py` to construct a sliding window history (excluding the final query) and pass it to the rewriter.

## Capabilities

### New Capabilities
- `query-rewriting-memory`: Adding context awareness to the query rewriter by processing a sliding window of conversation history.

### Modified Capabilities
- `semantic-caching`: Enhancing the quality of cached vector keys by providing highly specific, standalone rewritten queries.

## Impact

- `backend/app/api/chat.py`: Will construct and pass recent history to the rewriter.
- `backend/app/services/rewriting/base.py`: Add `history` parameter to interface.
- `backend/app/services/rewriting/llm_rewriter.py`: Update the signature and prompt template.
- Minimal impact on latency as it only alters an existing LLM prompt without adding new network calls.
