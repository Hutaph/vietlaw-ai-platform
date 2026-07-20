## Why

Currently, the Legal QA System provides answers and appends all retrieved legal documents to the frontend as "Context Used". However, users in the legal domain require absolute reliability and trust. They need to know exactly which clause or article was used to generate each part of the answer, and they should be able to cross-reference it directly. By forcing the LLM to output strict citation tags tied to specific document IDs and intercepting these tags to filter the provided context, we build a highly trustworthy "Legal Assistant" rather than just a chatbot.

## What Changes

- Modify the system prompt in the backend to instruct the LLM to use explicit XML citation tags (e.g., `<cite id="[ID]">Tên Điều/Khoản</cite>`).
- Enhance the RAG context builder to embed the source database ID into the context blocks fed to the LLM.
- Add an interceptor in the chat API pipeline to extract the document IDs from the LLM's XML tags using Regex.
- Filter the `contextUsed` array sent to the frontend so it only includes the documents that were explicitly cited by the LLM.

## Capabilities

### New Capabilities
- `strict-citation`: The capability to format generated answers with explicit references mapping back to exact source documents, and filtering the returned payload to only include used contexts.

### Modified Capabilities

## Impact

- **Backend / LLM Module**: `app/services/llm.py` (system prompt changes), `app/services/rag.py` (context formatting changes).
- **Backend / API Module**: `app/api/chat.py` (interceptor logic added before returning the payload).
- **Frontend Contract**: The `text` field in the API response will now contain `<cite id="...">` tags, and the `contextUsed` list will only include documents actually referenced, reducing payload size and improving relevance.
