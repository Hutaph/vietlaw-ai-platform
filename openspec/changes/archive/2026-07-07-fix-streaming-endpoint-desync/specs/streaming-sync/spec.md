# Streaming Endpoint Sync

## Purpose
This capability defines the required behaviors for the backend streaming endpoint (`/chat/stream`) and the frontend chat interface to ensure that they are fully synchronized with the advanced RAG features (Query Rewriting, Semantic Caching, Strict Citation) previously implemented only in the non-streaming pipeline.

## Requirements

### Requirement: Context-aware query rewriting in Streaming
The streaming endpoint MUST pass a sliding window of recent conversation history to the query rewriter before retrieving documents, to resolve anaphoric references properly.

#### Scenario: Rewriting with history in stream
- **WHEN** the user sends a query to the `/chat/stream` endpoint with a conversation history
- **THEN** the system constructs `recent_history_str` (e.g. last 4 messages)
- **AND** calls the rewriter with both the latest query and the history

### Requirement: Semantic Caching in Streaming
The streaming endpoint MUST intercept user queries, generate their embeddings, and check the semantic cache BEFORE calling the retrieval engine or the LLM. If a cache hit occurs, it MUST stream the cached response instead.

#### Scenario: Cache Hit in streaming
- **WHEN** the user submits a query to `/chat/stream` that hits the semantic cache
- **THEN** the backend immediately yields the cached context via SSE
- **AND** simulates streaming the cached response text via SSE tokens
- **AND** bypasses the standard retrieval and LLM generation phases

#### Scenario: Cache Miss in streaming
- **WHEN** a cache miss occurs
- **THEN** the backend runs the standard RAG pipeline, streams the LLM tokens
- **AND** writes the new response to the semantic cache after the stream completes

### Requirement: Client-side Citation Filtering
The frontend `ChatInterface` MUST parse the incoming LLM token stream for `<cite id="...">` tags and dynamically filter the displayed context list to only include cited documents.

#### Scenario: Dynamic context filtering on the client
- **WHEN** the frontend receives tokens from the SSE stream
- **THEN** it parses the accumulated text for citation tags
- **AND** updates the UI to display only the context items whose IDs are matched in the text, hiding unused context.
