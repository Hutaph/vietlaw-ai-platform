# VietLaw AI Platform

![Status](https://img.shields.io/badge/status-deployable-brightgreen)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Vercel](https://img.shields.io/badge/Frontend-Vercel-black?logo=vercel)
![Render](https://img.shields.io/badge/Backend-Render-46E3B7?logo=render&logoColor=111)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-supported-4169E1?logo=postgresql&logoColor=white)
![Qdrant](https://img.shields.io/badge/Vector_DB-Qdrant-DC244C)
![RAG](https://img.shields.io/badge/RAG-hybrid_search-blueviolet)

VietLaw AI Platform is a Vietnamese legal question-answering product powered by
Retrieval-Augmented Generation (RAG). It retrieves Vietnamese legal provisions
from Qdrant, reranks the best passages, stores document and chat metadata in
PostgreSQL, and generates Vietnamese answers with cited sources.

> Legal notice: VietLaw AI is an academic and portfolio product. It is not a
> professional legal advice service. Users should verify official legal texts or
> consult a qualified professional before making legal decisions.

![VietLaw AI overview](overview.png)

## Features

- Vietnamese-first legal chatbot with cited legal sources.
- Next.js 15 frontend with chat, document, and admin screens.
- FastAPI backend with modular RAG services.
- Qdrant dense/sparse retrieval and PostgreSQL persistence.
- Local BGE-M3 embedding and cross-encoder reranker support.
- Manual, resumable corpus ingestion with count verification.
- Backend-managed inference keys; provider secrets never need to be exposed in
  the browser.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, LangChain-compatible services |
| Retrieval | Qdrant hybrid vector search, local FAISS fallback |
| Storage | PostgreSQL / Supabase |
| Models | Local Hugging Face embedding and reranker artifacts, remote LLM providers |
| Deployment | Vercel frontend, Render/container backend, Docker Compose for local runs |

## Architecture

```text
User
  |
  v
Next.js frontend
  - Chat UI
  - Admin and document screens
  - API proxy routes
  |
  v
FastAPI backend
  - Query rewriting
  - Embedding
  - Hybrid retrieval
  - Reranking
  - Context building
  - Answer generation
  |
  +--> PostgreSQL: documents, clauses, chat history
  +--> Qdrant: dense and sparse vectors
  +--> Local models or remote inference providers
```

Production is split by design: Vercel serves the frontend, while the FastAPI
backend runs on a container host such as Render, Railway, Fly.io, Cloud Run, ECS,
or a VPS. PostgreSQL can run on Supabase and vectors can run on Qdrant Cloud.

## Repository

```text
.
├── backend/             # FastAPI app, RAG services, scripts, tests
├── frontend/            # Next.js app, components, API proxy routes
├── corpus/              # Processed legal corpus mounted for ingestion
├── docs/                # Technical and evaluation notes
├── fine-tuning/         # Embedding and reranker training artifacts
├── models/              # Local model artifacts, ignored from Git
├── docker-compose.yml   # Local full-stack runtime
├── render.yaml          # Render backend blueprint
├── vercel.json          # Vercel frontend build config
└── .env.example         # Environment template
```

## Requirements

- Docker Desktop
- Node.js 20 for native frontend development
- Python 3.11 for native backend development
- PostgreSQL or Supabase
- Qdrant local or Qdrant Cloud
- Backend provider keys for answer generation
- Optional NVIDIA GPU for faster local embedding and ingestion

## Environment

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Fill in the deployment values and keep `.env` out of Git.

| Variable | Purpose |
| --- | --- |
| `APP_URL` | Public frontend URL allowed by the backend. |
| `BACKEND_URL` | Backend URL used by frontend API proxy routes. |
| `CHAT_STORAGE_MODE` | `postgres` for shared history or `browser` for local browser history. |
| `STORAGE_BACKEND` | `qdrant_postgres` for production retrieval persistence. |
| `POSTGRES_DSN` | PostgreSQL connection string. Use `sslmode=require` for Supabase. |
| `QDRANT_URL` | Qdrant endpoint. |
| `QDRANT_API_KEY` | Qdrant Cloud API key. Empty for local Qdrant. |
| `QDRANT_COLLECTION` | Active legal clause collection. |
| `GOOGLE_API_KEY` | Google AI Studio key for Gemini-compatible answer generation. |
| `HUGGINGFACE_API_KEY` | Hugging Face token for remote model access. |
| `HUGGINGFACE_EMBEDDING_MODEL` | Local embedding path or remote model ID. |
| `RERANKER_MODEL` | Local cross-encoder reranker path. |
| `EMBEDDING_DEVICE` | `cpu` or `cuda`. |

Typical local Docker model paths:

```env
HUGGINGFACE_EMBEDDING_MODEL=/models/embedding/vietlaw-bge-m3-finetuned/best
RERANKER_MODEL=/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/checkpoint-3306
```

## Run Locally

Start the full stack:

```powershell
docker compose up --build
```

Open:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Run services separately when needed:

```powershell
docker compose up backend
docker compose up frontend
```

Run the frontend natively:

```powershell
cd frontend
npm install
npm run dev
```

For native frontend development, set:

```env
BACKEND_URL=http://localhost:8000
```

## Ingest Data

The backend is configured to avoid automatic ingestion on startup. Load or resume
the corpus manually:

```powershell
docker compose --profile tools run --rm ingest
```

The ingestion script reads `corpus/processed/legal-corpus.jsonl`, writes
documents and clauses to PostgreSQL, embeds missing clauses, upserts vectors to
Qdrant, and verifies final record/vector counts.

## Deploy

### Frontend: Vercel

Deploy `frontend/` as the Vercel project root. The included `vercel.json`
matches that layout.

Recommended settings:

```text
Framework preset: Next.js
Install command: npm ci
Build command: npm run build
Output directory: .next
Root directory: frontend
```

Set only frontend-safe variables on Vercel:

```env
BACKEND_URL=https://your-backend.example.com
NEXT_PUBLIC_CHAT_STORAGE_MODE=browser
```

### Backend: Render or Container Host

`render.yaml` defines the FastAPI backend as a Docker web service with
`/health` as the health check path.

Required backend variables:

```env
APP_URL=https://your-vercel-app.vercel.app
STORAGE_BACKEND=qdrant_postgres
POSTGRES_DSN=postgresql://...
QDRANT_URL=https://...
QDRANT_API_KEY=...
QDRANT_COLLECTION=vietlaw_clauses_v4
GOOGLE_API_KEY=...
HUGGINGFACE_API_KEY=...
DISABLE_AUTO_INGEST=true
ENABLE_FAISS_FALLBACK=false
```

Keep PostgreSQL, Qdrant, Google, Hugging Face, and OpenAI secrets on the backend
host only.

## Validate

Frontend:

```powershell
cd frontend
npm run build
npm run lint
```

Backend:

```powershell
docker compose build backend
```

Ingestion:

```powershell
docker compose --profile tools run --rm ingest
```

Before sharing a deployment, confirm the frontend can reach `BACKEND_URL`, the
backend health check passes, and PostgreSQL/Qdrant counts match the processed
corpus.
