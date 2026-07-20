## ADDED Requirements

### Requirement: Context ID Injection
The system SHALL inject the unique document ID into the context string provided to the LLM for each retrieved document.

#### Scenario: RAG context building
- **WHEN** the `build_nested_context` function formats retrieved documents
- **THEN** each document block must include a clear identifier in the format `[CĂN CỨ ID: <document_id>]`

### Requirement: Strict LLM Citation Format
The system prompt SHALL instruct the LLM to cite any used context using the exact XML tag format `<cite id="<document_id>">text</cite>`.

#### Scenario: LLM generating an answer using context
- **WHEN** the LLM generates a response based on provided context
- **THEN** it must include the citation tag `<cite id="<document_id>">` for any referenced legal clause

### Requirement: Context Filtering Interceptor
The chat endpoint SHALL intercept the LLM response, extract all cited document IDs, and filter the returned context payload to include only the cited documents.

#### Scenario: Returning filtered context to frontend
- **WHEN** the chat API prepares the response payload
- **THEN** the `contextUsed` array must contain only documents whose IDs match the IDs extracted from the `<cite>` tags in the LLM's response text.
- **AND THEN** if the LLM output contains no citations, the system should either return an empty `contextUsed` array or fallback to returning no context (to prevent showing irrelevant information).
