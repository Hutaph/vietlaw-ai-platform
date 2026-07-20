## Context

Currently, the legal QA system feeds retrieved documents to the LLM and the frontend indiscriminately. However, since the system serves legal contexts, absolute reliability is required. The LLM must explicitly cite what clauses it used to formulate its response, and the frontend must only display those exact clauses for user verification.

## Goals / Non-Goals

**Goals:**
- Enforce strict citation formatting via the LLM prompt.
- Reliably map LLM citations back to database documents via unique IDs.
- Filter the `contextUsed` payload in the chat API response to only include documents the LLM actually cited.

**Non-Goals:**
- Modifying the frontend UI component logic (this design focuses on backend data contracts).
- Changing the retrieval logic (Qdrant/BM25) - the initial pool of retrieved documents remains unchanged.

## Decisions

1. **Citation Format (XML Tags)**: We will instruct the LLM to output citations in the form `<cite id="[ID]">text</cite>`. 
   - *Rationale*: XML tags are easily matched via Regex in standard strings, and they are robust enough that streaming partial responses won't break the entire parsing pipeline (unlike JSON).
   - *Alternative Considered*: Structured JSON output. Rejected because it can delay streaming responses to the frontend.

2. **Context Block ID Injection**: In `rag.py`, we will modify the context string sent to the LLM to explicitly include `[CĂN CỨ ID: {clause_id}]` instead of just an index `[CĂN CỨ #{i}]`.
   - *Rationale*: This gives the LLM the exact string needed to fulfill the `<cite id="...">` requirement.

3. **API Interceptor (Regex Filter)**: In `chat.py`, we will use `re.finditer` to find all matches of `<cite id="(.*?)">` in the generated text, collect the IDs, and filter `frontend_context` to include only those IDs.
   - *Rationale*: Simple, fast, and stateless.

## Risks / Trade-offs

- **Risk: LLM Hallucination of IDs** -> *Mitigation*: The system prompt will strictly instruct the LLM to only use IDs provided in the `[CĂN CỨ ID: ...]` blocks. Any unmatched IDs in the regex filter will be safely ignored (the context just won't be returned).
- **Risk: LLM forgetting to use XML tags** -> *Mitigation*: The prompt is updated to make this a MANDATORY rule, with examples provided.
