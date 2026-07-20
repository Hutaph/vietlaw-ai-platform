# user-configurable-inference-roles Specification

## Purpose
TBD - created by archiving change add-user-configurable-inference-roles. Update Purpose after archive.
## Requirements
### Requirement: Browser-local provider credentials
The system SHALL allow users to configure supported LLM provider API keys in browser storage and SHALL NOT require those user-provided keys to be stored server-side.

#### Scenario: User saves provider key on this device
- **WHEN** a user enters a Google AI Studio or HuggingFace API key and chooses to remember it on this device
- **THEN** the frontend stores the key in browser-local storage for that browser profile.

#### Scenario: User uses session-only provider key
- **WHEN** a user enters a provider API key without choosing to remember it on this device
- **THEN** the frontend stores the key only for the current browser session.

#### Scenario: User clears provider configuration
- **WHEN** a user clears provider settings
- **THEN** the frontend removes stored provider API keys and role assignments from browser storage.

### Requirement: Role-based inference model assignment
The system SHALL allow users to assign provider and model choices separately for answer generation, query rewriting, and memory summarization.

#### Scenario: Assigning distinct role models
- **WHEN** a user configures different provider/model pairs for the answer, rewriter, and summarizer roles
- **THEN** the frontend saves each role assignment independently.

#### Scenario: Reusing answer model for helper roles
- **WHEN** a user chooses to use the answer model for helper roles
- **THEN** the frontend applies the answer provider/model to the rewriter and summarizer role settings.

#### Scenario: Missing answer role configuration
- **WHEN** no usable answer role provider/model is configured
- **THEN** the frontend treats inference setup as incomplete.

### Requirement: Provider setup popup
The system SHALL show a setup popup when a user enters the web app without a usable answer role configuration.

#### Scenario: First visit without provider setup
- **WHEN** a user opens the chat UI and no answer role configuration exists
- **THEN** the frontend displays a setup popup explaining that the user must configure a supported provider and model before inference can run.

#### Scenario: Completed setup
- **WHEN** a user has a usable answer role configuration
- **THEN** the frontend allows the user to use the chat UI without blocking on the setup popup.

#### Scenario: Setup explains key storage
- **WHEN** the setup popup is displayed
- **THEN** it informs the user that user-provided API keys are stored in the current browser and sent to the backend only for inference requests.

### Requirement: Per-request runtime inference configuration
The system SHALL send the selected role provider/model configuration and required provider credentials to the backend with each chat request.

#### Scenario: Chat request includes role config
- **WHEN** a user sends a chat message after configuring inference roles
- **THEN** the request payload includes runtime configuration for the answer, rewriter, and summarizer roles.

#### Scenario: Backend does not persist user keys
- **WHEN** the backend receives user-provided provider credentials in a chat request
- **THEN** it uses those credentials only for the current inference workflow and does not persist them to storage.

#### Scenario: Backend redacts user keys
- **WHEN** backend validation, logging, or error handling references runtime inference configuration
- **THEN** user-provided provider API keys MUST NOT be logged, echoed in responses, or included in persisted chat/session data.

### Requirement: Fixed deployed embedding stack
The system SHALL keep the deployed embedding provider/model fixed to HuggingFace `BAAI/bge-m3` and SHALL NOT expose runtime embedding provider or model selection in user inference settings. Runtime HuggingFace credentials MAY still be used as the API key source for that fixed embedding stack.

#### Scenario: User changes LLM roles
- **WHEN** a user changes answer, rewriter, or summarizer provider/model settings
- **THEN** retrieval continues to use the server-managed HuggingFace `BAAI/bge-m3` embedding stack.

#### Scenario: Runtime request omits embedding override
- **WHEN** the frontend sends runtime inference configuration to the backend
- **THEN** the payload does not include an embedding provider or embedding model override.

#### Scenario: Remote-first does not use local embedding fallback
- **WHEN** retrieval runs with `INFERENCE_STRATEGY=remote_first`
- **THEN** the backend does not use Ollama local embeddings as a fallback for HuggingFace `BAAI/bge-m3`.

