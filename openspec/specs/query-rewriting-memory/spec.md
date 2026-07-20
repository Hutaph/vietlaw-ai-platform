# Query Rewriting Memory

## Purpose
This capability describes the context-aware query rewriting mechanism that uses a sliding window of conversation history to resolve pronouns and implicit references, generating precise standalone legal queries for RAG retrieval.

## Requirements

### Requirement: Context-aware query rewriting via sliding window
The system SHALL intercept user queries and, if a conversation history exists, provide a sliding window of recent conversation turns to the `LLMRewriter` component. The rewriter MUST use this history to resolve anaphoric references and output a standalone, formal legal query for the current turn.

#### Scenario: User asks a follow-up query with pronouns
- **WHEN** a user asks a follow-up query that contains pronouns or implicit context referencing the immediately preceding turn (e.g., "Mức phạt là bao nhiêu?")
- **THEN** the system passes the recent history to the query rewriter
- **AND** the rewriter generates a standalone legal query that includes the resolved context (e.g., "Mức xử phạt đối với hành vi điều khiển xe máy vi phạm nồng độ cồn")
