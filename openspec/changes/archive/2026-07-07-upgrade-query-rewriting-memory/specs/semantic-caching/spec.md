## MODIFIED Requirements

### Requirement: Semantic cache check before RAG pipeline execution
The system SHALL intercept user queries after the query rewriting step, generate an embedding for the contextually-resolved standalone rewritten query, and query the semantic cache collection. If a match exceeds the configured similarity threshold, the system MUST return the cached response text and its associated citation context (`contextUsed`), bypassing the standard vector search and LLM generation phases.

#### Scenario: Cache hit with high similarity
- **WHEN** the user submits a query whose contextually-resolved rewritten form has a cosine similarity greater than or equal to `SEMANTIC_CACHE_THRESHOLD` compared to a cached query
- **THEN** the system immediately returns the cached response text and citation context
- **AND** standard retrieval and LLM generation steps are not executed

#### Scenario: Cache miss or low similarity
- **WHEN** the user submits a query whose contextually-resolved rewritten form has a cosine similarity below `SEMANTIC_CACHE_THRESHOLD` or no matches exist in the cache
- **THEN** the system executes the standard RAG pipeline (search, rerank, context build, LLM generate)
- **AND** the new response and context are saved to the semantic cache collection to serve future identical queries
