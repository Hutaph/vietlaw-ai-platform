## Context

Currently, the conversational memory in the Vietnam Legal QA System is implemented by concatenating all previous messages into a single raw text string (`chat_history_str`) and passing it to the main `CHAT_PROMPT`. While this retains 100% of the conversation context, it scales linearly with the number of turns, quickly bloating the prompt size. This results in higher LLM token usage, slower generation speeds, and attention dilution, especially when processing legal documents in Agentic RAG workflows. 

## Goals / Non-Goals

**Goals:**
- Reduce token consumption for long conversational sessions.
- Maintain a high-quality summary of the entire session to prevent context loss.
- Prevent latency increases for the user by executing the summarization asynchronously.

**Non-Goals:**
- Completely overhauling the vector search architecture.
- Implementing complex multi-user persistent memory (this remains strictly session-scoped).

## Decisions

1. **Hybrid Memory Architecture (Summary + Sliding Window):**
   - The LLM prompt will receive a `summary` of the distant past and only the last `N` raw messages (e.g., 4 messages = 2 turns) verbatim.
   - *Rationale:* This preserves granular details for the most recent back-and-forth while keeping a compact context of older interactions.

2. **Asynchronous Summarization (Summarizer Agent):**
   - A dedicated summarization function (`update_memory_summary`) will be created.
   - It will be triggered using `asyncio.create_task` at the end of `/chat` and `/chat/stream` execution, avoiding any blocking of the HTTP response or Server-Sent Events stream.
   - *Rationale:* Memory updates shouldn't penalize user response latency.

3. **Storage Strategy (PostgreSQL):**
   - A new table `chat_sessions` will be added to `backend/app/services/storage.py` (or extending an existing one) to track `session_id`, `summary`, and `turn_count`.
   - *Rationale:* We already use PostgreSQL for feedback storage, making it the perfect place for stateful session persistence.

## Risks / Trade-offs

- **Risk:** Summarization implies a second LLM API call per turn, increasing compute costs.
  - *Mitigation:* The Summarizer Agent can use a much smaller, cheaper model (like `qwen2.5:1.5b` or `gpt-4o-mini`) via the existing `get_llm()` factory, and only trigger periodically (e.g., every 3-4 turns) instead of every single turn.
- **Risk:** Over-compression might lead to loss of specific details mentioned early in the conversation.
  - *Mitigation:* Crucial entities should be explicitly mentioned in the summarization prompt instructions to ensure they are retained.
