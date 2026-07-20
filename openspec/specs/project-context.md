# Project Context for OpenSpec

## 1. Overview

VietLaw AI is a Vietnamese legal QA system built as a client-server application with a RAG pipeline. The system retrieves relevant legal clauses from a local legal corpus, builds context, and sends the result to an LLM for answer generation.

The project is currently focused on:
- legal question answering
- citation-oriented responses grounded in legal documents
- Vietnamese UI and user chat sessions
- retrieval and reranking over a local processed legal corpus

## 2. Tech stack

### Backend
- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic
- LangChain / LangChain Core / LangChain Community
- Hugging Face integrations for embeddings and LLMs
- FAISS via faiss-cpu
- python-dotenv

### Frontend
- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- Lucide React
- React Markdown
- Motion

### Infra / data
- Docker Compose support
- Local JSON-based legal dataset under backend/data/processed
- FAISS index stored locally under backend/vietlaw_faiss_index
- Environment variables loaded from a root .env file

## 3. Repository structure

- backend/: FastAPI backend and RAG services
  - app/api/: API routers
  - app/services/: domain logic for pipeline, search, reranking, LLM, chunking, embedding, knowledge base
  - app/models.py: Pydantic request/response models
  - app/config.py: centralized configuration and environment variables
  - data/processed/: processed legal JSON documents
  - data/raw/: raw data folder
- frontend/: Next.js app router frontend
  - app/api/chat/route.ts: proxy route to backend
  - components/chat/: chat UI components
  - hooks/: reusable React hooks
  - lib/: shared constants, types, and utilities
- openspec/: OpenSpec workspace for change proposals and specs
- embedding/, reranking/, fine-tuning/: experiment and training assets

## 4. Architecture and module responsibilities

### Backend flow
1. Frontend sends a chat request to /api/chat.
2. Backend route extracts the latest user message and chat history.
3. The RAG pipeline performs retrieval, reranking, and context construction.
4. The LLM is invoked with the assembled context and a legal-answering system prompt.
5. The completed user/assistant turn is persisted to PostgreSQL before the client receives completion.
6. The response is returned as plain text plus contextUsed metadata.
7. The memory manager may summarize the turn asynchronously after response completion.

### Main backend modules
- app/api/chat.py: HTTP endpoint handling for chat, streaming, and session management
- app/services/pipeline.py: orchestrates retrieval → reranking → context building
- app/services/knowledge_base.py: loads legal data into memory and provides metadata lookup
- app/services/llm.py: LLM client setup and prompt templates
- app/services/search/: retrieval strategies such as FAISS, BM25, and hybrid search
- app/services/reranking/: reranker implementations
- app/services/context_builder/: builds legal context for answer generation
- app/services/chunking/: document chunking logic
- app/services/embedding/: embedding provider abstraction
- app/services/storage.py: database abstraction for PostgreSQL and Qdrant
- app/services/memory_manager.py: handles asynchronous chat history summarization
- app/services/semantic_cache.py: manages Qdrant-backed semantic caching for LLM responses

### Frontend modules
- components/chat/ChatInterface.tsx: main chat experience and input handling
- hooks/use-chat-sessions.ts: session state, active-session restore, lazy message loading, and browser-cache reconciliation with PostgreSQL
- lib/types.ts: shared TypeScript interfaces
- lib/constants.ts: categories, models, and storage keys

## 5. Coding conventions

### Python conventions
- Follow a modular service-oriented structure.
- Keep API routes thin; avoid putting business logic directly into route handlers.
- Prefer single-responsibility modules.
- Use snake_case for Python functions and variables.
- Use Pydantic models for request/response validation.
- Keep configuration in app/config.py rather than hardcoding values.
- Use the existing logger setup from app/utils/logging.py.
- Add Vietnamese comments where the codebase already uses them.

### TypeScript / React conventions
- Use functional components and hooks.
- Keep UI components presentational where possible.
- Move session/state logic into hooks rather than keeping it inside large components.
- Use shared types under lib/types.ts and shared constants under lib/constants.ts.
- Keep UI copy in Vietnamese to match the product language.

## 6. API conventions

### Backend API
- Primary endpoint: POST /chat and POST /chat/stream
- Request body shape:
  - messages: array of { role, content }
  - model: selected model identifier
  - category: legal category filter, default "all"
  - sessionId: identifier for chat session
- Response shape:
  - text: generated answer
  - contextUsed: list of retrieved legal context items
- Session Management endpoints:
  - GET /chat/sessions: retrieves list of chat sessions
  - GET /chat/session/{session_id}/messages: retrieves message history
  - DELETE /chat/session/{session_id}: deletes a chat session

### Frontend proxy API
- The Next.js route at frontend/app/api/chat/route.ts forwards requests to the backend.
- Additional Next.js proxy routes in frontend/app/api/chat/sessions/ allow frontend to sync session data with the backend database.
- Frontend client calls /api/chat and expects the same response format.
- Error responses should carry a clear error and details payload.

## 7. Development, build, and test workflow

### Backend
- Run from backend/ directory
- Start dev server:
  - python main.py
  - or uvicorn app.main:app --reload
- Install dependencies:
  - pip install -r requirements.txt

### Frontend
- Install dependencies:
  - npm install
- Start dev server:
  - npm run dev
- Build:
  - npm run build
- Lint:
  - npm run lint

### Docker
- From repository root:
  - docker-compose up --build

### Testing status
- No dedicated automated test suite is currently visible in the repository.
- Future feature work should add tests explicitly rather than relying on manual verification only.

## 8. Data model and storage

### Current data storage approach
- **PostgreSQL**: Used as the primary relational database to store legal metadata, clause text, chat sessions, chat messages, and memory summaries.
- **Qdrant**: Used as the vector database for hybrid search (dense and sparse vectors) and semantic caching.
- **FAISS & JSON fallback**: The system retains backward compatibility with local FAISS index and JSON files if database services are unavailable.

### Current data shape
- PostgreSQL `laws` and `clauses` tables store the corpus text and metadata.
- PostgreSQL `chat_sessions` and `chat_messages` tables store conversational history.
- Qdrant points store dense (BAAI/bge-m3) and sparse (BM25) vector representations.
- Semantic cache uses a separate Qdrant collection to map previously answered query vectors to their LLM responses.

### Chat session consistency
- The frontend keeps the active session id in browser storage so a refresh can restore the conversation the user was viewing.
- Opening the app without an active session starts from a blank new-chat state that is not inserted into the sidebar until a message is created.
- Historical messages are lazy-loaded from PostgreSQL when a session is selected.
- Cached browser messages are used for fast rendering, but PostgreSQL is authoritative when it reports a larger `message_count`.
- The backend persists the complete user/assistant turn before returning `/chat` or emitting the final `/chat/stream` `done` event.
- Background summarization remains asynchronous and updates session summaries after the completed turn is available.

### Important note
- Start the database services using Docker (`docker compose up -d postgres qdrant`) and ingest data with `scripts/ingest_to_storage.py` for the optimal persistence layer.

## 9. Authentication and permissions

- No authentication system is currently implemented.
- No role-based permission model is present.
- The application is effectively open and local-session based for now.
- Any future auth feature should be introduced explicitly and documented as a new capability.

## 10. Existing product behavior and UI conventions

- The UI is a single-page chat experience with a sidebar for chat sessions.
- Chat sessions persist in the backend PostgreSQL database. The frontend fetches and synchronizes state via API proxies.
- Refreshing while viewing an existing conversation restores that active session and must not merge messages into another session.
- Background tasks on the backend automatically summarize chat sessions to compress context length for long conversations.
- Users can select a legal category and an LLM provider/model.
- Responses may include legal context references.
- The UI is Vietnamese-first and should remain consistent with that language.

## 11. Implementation notes for future features

When implementing a new feature, keep the following in mind:
- Prefer extending the existing modular service architecture rather than adding logic directly to the route layer.
- Preserve the existing request/response format unless a breaking change is intentionally planned.
- Keep new configuration values in app/config.py and support them through environment variables.
- For new backend capabilities, add or update Pydantic models and keep route handlers thin.
- For new frontend features, keep state and persistence in hooks where possible.
- Avoid introducing a database or auth layer unless the feature genuinely requires it.
- If the feature changes retrieval behavior, validate that the pipeline still returns usable context and citations.
- If the feature changes UI behavior, preserve the current chat-first experience and local-session workflow unless explicitly redesigning it.
- Add documentation and tests for any new behavior because the project currently lacks an obvious automated test baseline.
