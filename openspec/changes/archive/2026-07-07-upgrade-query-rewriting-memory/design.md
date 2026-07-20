## Context

The current `LLMRewriter` component in our RAG pipeline evaluates user queries in isolation. This stateless behavior is detrimental in conversational contexts where a user asks follow-up questions referencing previous messages (e.g., "Mức phạt là bao nhiêu?" following a discussion about drunk driving). The semantic caching layer also suffers because these context-less queries pollute the cache with generic, unusable keys.

## Goals / Non-Goals

**Goals:**
- Inject conversational history into the query rewriting process without adding an additional round-trip to the LLM.
- Improve the specificity of rewritten queries to ensure high-quality vector retrieval.
- Enhance semantic caching efficacy by ensuring cache keys (rewritten queries) are contextually complete.

**Non-Goals:**
- Implementing a separate "standalone query generator" node.
- Feeding the entirety of long conversations into the rewriter (which would dilute the LLM's focus and increase costs).

## Decisions

**1. Pass Conversation History to LLMRewriter via Sliding Window**
- *Rationale*: Modifying `LLMRewriter` to accept an optional `history` parameter allows us to prepend a subset of recent messages into the prompt. A sliding window of the last 2 turns (last 4 messages) provides sufficient context for resolving pronouns and anaphoric references without exceeding prompt length limits or diluting instructions.
- *Alternatives Considered*: Creating a dedicated Context Resolver node. This was rejected because it adds unnecessary latency (two sequential LLM calls before retrieval).

**2. Update Prompt Template in LLMRewriter**
- *Rationale*: The `ChatPromptTemplate` will be updated to instruct the model to review the provided history before rewriting the current query into a formal, standalone legal query. 

**3. Modify chat endpoint to extract history for rewriter**
- *Rationale*: In `backend/app/api/chat.py`, we already construct `chat_history_str` for the final answering LLM. We will pass this same string (or a truncated version of it) to the `rewrite()` method.

## Risks / Trade-offs

- **[Risk] Prompt Dilution**: Providing too much history might confuse the rewriting model, causing it to output summaries of the history rather than a search query for the current turn.
  - *Mitigation*: Strictly limit the history passed to the rewriter to the last 2 turns (sliding window) and explicitly instruct the model to focus ONLY on generating a query for the "Current User Query".
- **[Risk] Increased Token Usage**: Adding history slightly increases input tokens to the rewriting LLM.
  - *Mitigation*: The increase is marginal (a few dozen tokens) and the improved cache hit rate and retrieval accuracy outweigh the negligible cost.
