# VietLaw AI Platform

VietLaw AI Platform is a Vietnamese legal question-answering system built with
Retrieval-Augmented Generation (RAG). It indexes Vietnamese legal clauses,
retrieves dense and sparse matches from Qdrant, reranks candidate passages, and
generates Vietnamese answers with source citations.

> Legal notice: this project is an academic and portfolio system. It is not a
> professional legal advice service. Users should verify official legal texts or
> consult a qualified professional before making legal decisions.

![VietLaw AI overview](overview.png)

## Highlights

- Vietnamese-first legal chatbot UI with cited legal sources.
- FastAPI backend with configurable RAG pipeline.
- Next.js 15 frontend ready for Vercel deployment.
- PostgreSQL-backed document and chat metadata.
- Qdrant dense/sparse hybrid retrieval with named vectors.
- Fine-tuned local BGE-M3 embedding and cross-encoder reranker support.
- Robust ingestion flow with resume checks, batch upsert, and final count
  verification.
- Server-managed inference keys so users do not need to paste provider API keys
  into the browser.

## Architecture

```text
User
  |
  v
Next.js frontend
  - Chat UI
  - Admin/document screens
  - API route proxies
  |
  v
FastAPI backend
  - Request validation
  - Query rewriting
  - Embedding
  - Qdrant retrieval
  - Reranking
  - Context building
  - LLM answer generation
  |
  +--> PostgreSQL: document metadata, clauses, chat history
  +--> Qdrant: dense and sparse vectors
  +--> Local models or remote inference providers
```

The production-friendly setup is split:

- Vercel hosts the `frontend` Next.js app.
- A long-running Python platform hosts the `backend` service.
- Supabase can host PostgreSQL.
- Qdrant Cloud can host vector search.
- Local embedding/reranker artifacts should run on a backend host that supports
  persistent storage and enough memory/GPU capacity.

## Repository Layout

```text
.
├── backend/                  # FastAPI backend and RAG services
│   ├── app/
│   │   ├── api/              # HTTP routers
│   │   ├── services/         # RAG, storage, search, reranking, LLM logic
│   │   ├── utils/            # Shared backend utilities
│   │   ├── config.py         # Runtime configuration
│   │   └── main.py           # FastAPI application factory
│   ├── scripts/              # Ingestion and maintenance scripts
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                 # Next.js 15 frontend
│   ├── app/                  # App Router pages and API proxy routes
│   ├── components/           # Chat, admin, document, and shared UI
│   ├── hooks/
│   ├── lib/
│   └── package.json
├── corpus/                   # Processed legal corpus mounted into Docker
├── docs/                     # Technical notes and evaluation docs
├── fine-tuning/              # Embedding/reranker fine-tuning notebooks
├── models/                   # Local model artifacts, ignored from Git
├── docker-compose.yml
├── vercel.json               # Vercel build config for the frontend
└── .env.example
```

## Prerequisites

- Docker Desktop
- Node.js 20 if running the frontend outside Docker
- Python 3.11 if running the backend outside Docker
- PostgreSQL, or a Supabase PostgreSQL project
- Qdrant, or a Qdrant Cloud cluster
- Provider API keys for answer generation, configured on the backend
- Optional NVIDIA GPU and working Docker GPU runtime for faster ingestion

## Environment Setup

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your own values. Never commit `.env`.

The most important variables are:

| Variable | Purpose |
| --- | --- |
| `BACKEND_URL` | Backend URL used by the Next.js API proxy routes. |
| `CHAT_STORAGE_MODE` | `postgres` for shared DB history, `browser` for local browser history. |
| `STORAGE_BACKEND` | `qdrant_postgres` for the cloud/vector database path. |
| `POSTGRES_DSN` | PostgreSQL connection string. Use `sslmode=require` for Supabase. |
| `QDRANT_URL` | Qdrant Cloud or local Qdrant endpoint. |
| `QDRANT_API_KEY` | Qdrant Cloud API key. Leave empty for local Qdrant. |
| `QDRANT_COLLECTION` | Active Qdrant collection name. |
| `GOOGLE_API_KEY` | Google AI Studio key for Gemini-compatible answer generation. |
| `HUGGINGFACE_API_KEY` | Hugging Face token for remote inference paths. |
| `HUGGINGFACE_EMBEDDING_MODEL` | Local embedding artifact path or remote model ID. |
| `RERANKER_MODEL` | Local cross-encoder artifact path. |
| `EMBEDDING_DEVICE` | `cpu` or `cuda`. Use `cuda` only when the backend host has GPU support. |

For local Docker runs, model paths usually look like:

```env
HUGGINGFACE_EMBEDDING_MODEL=/models/embedding/vietlaw-bge-m3-finetuned/best
RERANKER_MODEL=/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/checkpoint-3306
```

For native runs outside Docker, use paths relative to the repository root or
absolute host paths.

## Local Development

Start the full local stack:

```powershell
docker compose up --build
```

Run only the backend:

```powershell
docker compose up backend
```

Run only the frontend:

```powershell
docker compose up frontend
```

Open:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Backend health/docs depend on the FastAPI routes exposed by the backend.

If you run the frontend outside Docker:

```powershell
cd frontend
npm install
npm run dev
```

The frontend API routes proxy requests to `BACKEND_URL`. For local native
frontend development, set:

```env
BACKEND_URL=http://localhost:8000
```

## Ingesting the Corpus

The backend does not auto-ingest on startup when `DISABLE_AUTO_INGEST=true`.
This avoids slow and risky startup behavior.

Run ingestion manually:

```powershell
docker compose --profile tools run --rm ingest
```

The ingestion flow should:

1. Load `corpus/processed/legal-corpus.jsonl`.
2. Upsert document and clause records into PostgreSQL.
3. Check which clause vectors already exist in Qdrant.
4. Embed only missing clauses.
5. Batch upsert vectors into Qdrant.
6. Verify PostgreSQL clause count and Qdrant vector count.
7. Fail loudly when embedding, PostgreSQL, or Qdrant fails.

If ingestion is interrupted, rerun the same command. The resume check should
skip vectors that are already present and continue with the missing clauses.

## GPU Notes

CPU works, but embedding tens of thousands of clauses can be slow. A consumer
GPU such as an RTX 3060 can be much faster when Docker GPU runtime is working.

Check Docker GPU support:

```powershell
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

Use CUDA only after this succeeds:

```env
EMBEDDING_DEVICE=cuda
```

For local chat on a machine without a working NVIDIA runtime, use:

```env
EMBEDDING_DEVICE=cpu
RERANKER_DEVICE=cpu
```

## Vercel Deployment

This repository includes a root `vercel.json` that builds the Next.js frontend
from `frontend/`.

Recommended Vercel settings:

- Framework preset: Next.js
- Build command: `cd frontend && npm run build`
- Install command: `cd frontend && npm ci`
- Output directory: `frontend/.next`

Set these Vercel environment variables:

```env
BACKEND_URL=https://your-backend.example.com
NEXT_PUBLIC_CHAT_STORAGE_MODE=browser
```

Do not put PostgreSQL, Qdrant, Google, Hugging Face, or OpenAI secrets in
client-side variables. Keep provider keys on the backend host.

### Backend Hosting

The FastAPI backend should be deployed separately from Vercel because it may
need:

- Long-running Python workers.
- Local model files.
- GPU or high-memory CPU runtime.
- Stable outbound connections to Qdrant and PostgreSQL.
- Longer startup/readiness windows for local model loading.

Good backend targets include a VPS, Render, Railway, Fly.io, Google Cloud Run,
AWS ECS, or any container host that supports your model and startup needs.

Backend environment variables should include:

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

## Release Checklist

Before sharing the project with recruiters or reviewers:

- Ensure `.env` is not tracked by Git.
- Rotate any keys that were pasted into screenshots, logs, or chat history.
- Confirm Qdrant vector count matches the processed corpus clause count.
- Confirm PostgreSQL contains the expected documents and clauses.
- Run the backend and submit at least one real legal question.
- Run `npm run build` in `frontend`.
- Confirm Vercel has only frontend-safe environment variables.
- Confirm the deployed frontend can reach `BACKEND_URL`.
- Keep corpus licensing and legal-source provenance clear.

## Validation Commands

Frontend:

```powershell
cd frontend
npm run build
npm run lint
```

Backend container build:

```powershell
docker compose build backend
```

Frontend container build:

```powershell
docker compose build frontend
```

Ingestion:

```powershell
docker compose --profile tools run --rm ingest
```

## Troubleshooting

### The backend starts but chat fails

Check backend logs first. Common causes:

- `BACKEND_URL` in Vercel points to the wrong backend.
- The backend cannot connect to Supabase or Qdrant Cloud.
- Local model paths do not exist inside the container.
- `EMBEDDING_DEVICE=cuda` is set on a host without a working NVIDIA runtime.

### Qdrant has fewer vectors than PostgreSQL clauses

Rerun ingestion. The resume check should embed only missing clauses. If it still
fails, verify:

- `QDRANT_COLLECTION`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `QDRANT_TIMEOUT`
- embedding model path and required files

### Supabase cannot resolve or connect

Use the IPv4-compatible pooler URL when your network or Docker environment
does not support IPv6 direct connections. Supabase pooler URLs usually use port
`6543` and require SSL.

### Docker CUDA image fails

If a CUDA image reports that the driver does not satisfy the CUDA requirement,
either update the NVIDIA driver or test with an older CUDA image such as
`11.8.0-base-ubuntu22.04`.

## Security Notes

- Do not commit `.env`, database URLs, API keys, or Qdrant tokens.
- Do not expose provider keys through `NEXT_PUBLIC_*`.
- Keep answer-generation keys on the backend.
- Prefer separate development and production Qdrant collections.
- Rotate leaked keys immediately.

## Project Status

This project is being prepared as a personal portfolio release. The current
recommended production path is:

1. Vercel for the frontend.
2. A container host for the FastAPI backend.
3. Supabase PostgreSQL for relational data.
4. Qdrant Cloud for vector retrieval.
5. Server-managed inference credentials.
