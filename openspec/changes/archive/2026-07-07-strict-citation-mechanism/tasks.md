## 1. Update Context Builder and Frontend Formatter

- [x] 1.1 In `app/services/rag.py`, update `build_nested_context` to include `[CĂN CỨ ID: {clause_id}]` in the output for the LLM.
- [x] 1.2 In `app/services/rag.py`, update `format_docs_for_frontend` to include the document `id` field in the returned dictionary so it can be used for filtering.

## 2. Enforce Strict Prompt Rules

- [x] 2.1 In `app/services/llm.py`, update `CHAT_PROMPT` to add a MANDATORY RULE for citing used contexts with the XML tag format `<cite id="[ID]">text</cite>`.

## 3. Implement Chat API Interceptor

- [x] 3.1 In `app/api/chat.py`, parse the generated `output_text` with regex `r'<cite\s+id=["\']([^"\']+)["\']>'` to collect all cited document IDs.
- [x] 3.2 In `app/api/chat.py`, filter the `frontend_context` list to only retain items where their `id` matches the extracted cited IDs (fallback to returning all if no IDs are found, or return empty list depending on preference).
