## ADDED Requirements

### Requirement: Classify and rewrite user queries
The system SHALL intercept user queries and use an LLM-based agent to classify the domain (legal vs chitchat) and rewrite non-formal legal language into formal legal terminology.

#### Scenario: Translating slang to formal terminology
- **WHEN** a user asks a legal question using informal terms (e.g., "sổ đỏ")
- **THEN** the system SHALL output a JSON structure categorizing the domain as "legal" and providing an array of queries including the formal translation (e.g., "giấy chứng nhận quyền sử dụng đất")

#### Scenario: Routing non-legal chitchat
- **WHEN** a user sends a conversational or non-legal message (e.g., "Xin chào")
- **THEN** the system SHALL classify the domain as "chitchat" and return an empty query array to bypass document retrieval

#### Scenario: Fallback on parsing failure
- **WHEN** the rewriting LLM fails to return valid JSON
- **THEN** the system SHALL default to the "legal" domain and use the original user query for retrieval
