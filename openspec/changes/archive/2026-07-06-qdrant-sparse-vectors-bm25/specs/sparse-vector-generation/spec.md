## ADDED Requirements

### Requirement: Generate sparse vectors for legal clauses
The system SHALL generate sparse vectors (token-to-weight arrays) for each legal clause using a Vietnamese-compatible tokenizer and term-frequency counting.

#### Scenario: Sparse vector generation
- **WHEN** a legal clause is prepared for vector embedding
- **THEN** the system SHALL extract tokens, compute term weights, and output a valid dictionary of indices and values compatible with Qdrant's sparse vector format
