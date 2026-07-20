## ADDED Requirements

### Requirement: Explicit runtime profile selection

The system MUST support explicit local and serverless runtime profiles, and each profile MUST select only compatible embedding, reranking, model-loading, and dependency behavior.

#### Scenario: Local profile uses fine-tuned artifacts

- **WHEN** the backend starts with the local runtime profile
- **THEN** it uses the configured fine-tuned local embedding artifact and local cross-encoder reranker, validates their required files, and does not require Hugging Face API credentials for retrieval or reranking

#### Scenario: Serverless profile uses remote inference

- **WHEN** the backend starts with the serverless runtime profile
- **THEN** it uses Hugging Face API embedding and deployment-safe embedding-similarity reranking, does not load local model artifacts, and does not require local Ollama/model services

#### Scenario: Incompatible profile configuration

- **WHEN** a serverless profile is configured with local-only model settings or a local profile is missing its required artifact path
- **THEN** startup or readiness fails with a clear configuration error that identifies the incompatible setting without exposing credentials

### Requirement: Deployment dependency isolation

The system MUST provide a deployment dependency manifest that excludes local ML runtime packages and a local/Docker dependency path that installs the packages required by fine-tuned local inference.

#### Scenario: Serverless dependency installation

- **WHEN** the deployment platform installs the backend production requirements
- **THEN** the resulting dependency set does not include PyTorch, Transformers, Sentence Transformers, or local model weight runtimes that would inflate the serverless function bundle

#### Scenario: Local dependency installation

- **WHEN** a developer runs the documented local or Docker setup for the local profile
- **THEN** the base backend requirements and local ML extras are installed so the fine-tuned embedding and reranker can load successfully

### Requirement: Profile-aware readiness diagnostics

The system MUST report the active runtime profile and validate only the resources required by that profile in readiness diagnostics.

#### Scenario: Remote readiness without local artifacts

- **WHEN** readiness is checked for a serverless profile with valid remote configuration and Qdrant access
- **THEN** readiness does not fail because local embedding or reranker artifact directories are absent

#### Scenario: Local readiness with missing artifact

- **WHEN** readiness is checked for a local profile and a required fine-tuned artifact is missing or incomplete
- **THEN** readiness reports a not-ready state with the artifact validation failure

