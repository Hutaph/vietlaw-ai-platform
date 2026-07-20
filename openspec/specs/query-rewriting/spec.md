# Capability: Query Rewriting

## Purpose
TBD
## Requirements
### Requirement: Classify and rewrite user queries
The system SHALL intercept user queries and use the configured rewriter role LLM to classify the domain (legal vs chitchat) and rewrite non-formal legal language into formal legal terminology. When a runtime rewriter provider/model is configured in the chat request, the rewriter SHALL use that runtime role configuration for the current request.

#### Scenario: Translating slang to formal terminology
- **WHEN** a user asks a legal question using informal terms (e.g., "so do")
- **THEN** the system SHALL output a JSON structure categorizing the domain as "legal" and providing an array of queries including the formal translation (e.g., "giay chung nhan quyen su dung dat")

#### Scenario: Routing non-legal chitchat
- **WHEN** a user sends a conversational or non-legal message (e.g., "Xin chao")
- **THEN** the system SHALL classify the domain as "chitchat" and return an empty query array to bypass document retrieval

#### Scenario: Runtime rewriter role is configured
- **WHEN** a chat request includes a valid runtime provider/model for the rewriter role and query rewriting is enabled
- **THEN** the query rewriter invokes the configured rewriter role model for that request.

#### Scenario: Fallback on parsing failure
- **WHEN** the rewriting LLM fails to return valid JSON
- **THEN** the system SHALL default to the "legal" domain and use the original user query for retrieval

