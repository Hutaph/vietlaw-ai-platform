## MODIFIED Requirements

### Requirement: Deploy-Safe Remote Reranking

The system SHALL provide a remote-only reranking strategy for deployments without local inference. The remote strategy SHALL use the same request-scoped or server-fallback Hugging Face credential policy as embedding retrieval, and it SHALL never initialize a local cross-encoder in a remote/serverless profile.

#### Scenario: Embedding-similarity reranking is selected

- **WHEN** `PIPELINE_RERANKING=embedding_similarity` in a remote/serverless profile
- **THEN** the backend reranks retrieved documents by cosine similarity between Hugging Face `BAAI/bge-m3` query/document embeddings and uses the resolved reranker credential for every remote embedding call

#### Scenario: Cross-encoder is requested in remote-first deployment

- **WHEN** `PIPELINE_RERANKING=cross_encoder` and the active profile is remote/serverless
- **THEN** the backend normalizes the strategy to embedding-similarity or rejects the configuration before serving requests, and it does not load a local artifact or call a Hugging Face text-classification endpoint

#### Scenario: Remote reranker credential is missing

- **WHEN** remote reranking is enabled and neither a request-scoped nor server fallback Hugging Face credential is available
- **THEN** the backend returns a clear authentication/configuration error before issuing a remote reranking request

### Requirement: Retrieval embedding and reranking credential routing

The system SHALL resolve embedding and reranking credentials at the request boundary, pass them explicitly through the retrieval pipeline, and use the server environment credential only as the configured fallback. Local inference paths MUST ignore remote credentials and MUST NOT call Hugging Face.

#### Scenario: Request credential is available

- **WHEN** a chat request includes a valid Hugging Face credential for a remote embedding/reranking profile
- **THEN** retrieval and remote reranking use the intended request-scoped credential consistently for the entire request

#### Scenario: Request credential is absent

- **WHEN** a remote request omits a Hugging Face credential but a server fallback credential is configured
- **THEN** both embedding retrieval and remote reranking use the server fallback without logging or persisting the raw credential

#### Scenario: Local profile has no remote credential

- **WHEN** the local profile runs with no Hugging Face credential
- **THEN** local fine-tuned embedding and reranking continue to work without attempting a Hugging Face API request

