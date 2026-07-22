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
![Corpus](https://img.shields.io/badge/Corpus-52_law_texts-2E7D32)
![Structured Nodes](https://img.shields.io/badge/Data-52k_structured_nodes-1565C0)

VietLaw AI Platform là sản phẩm hỏi đáp pháp luật Việt Nam ứng dụng
Retrieval-Augmented Generation (RAG). Hệ thống truy xuất điều khoản pháp luật từ
Qdrant, rerank các đoạn liên quan nhất, lưu metadata tài liệu và lịch sử chat
trong PostgreSQL, rồi sinh câu trả lời tiếng Việt kèm nguồn trích dẫn.

> Lưu ý pháp lý: VietLaw AI là sản phẩm học thuật và portfolio, không phải dịch
> vụ tư vấn pháp lý chuyên nghiệp. Người dùng cần kiểm tra văn bản chính thức
> hoặc tham khảo chuyên gia trước khi đưa ra quyết định pháp lý.

![VietLaw AI overview](overview.png)

## Tính năng

- Chatbot pháp luật ưu tiên tiếng Việt, trả lời kèm nguồn trích dẫn.
- Frontend Next.js 15 với màn hình chat, tài liệu và quản trị.
- Backend FastAPI với các service RAG được tách module rõ ràng.
- Truy xuất dense/sparse trên Qdrant và lưu trữ metadata bằng PostgreSQL.
- Hỗ trợ embedding BGE-M3 và cross-encoder reranker chạy local.
- Ingest corpus thủ công, có khả năng resume và kiểm tra số lượng bản ghi/vector.
- Khóa inference được quản lý ở backend, không cần đưa secret ra trình duyệt.

## Dữ liệu

Corpus hiện tại là snapshot `g2-structured-corpus-20260713`, được parse từ các
văn bản pháp luật tiếng Việt lưu trong `corpus/raw/` và chuẩn hóa thành JSONL ở
`corpus/processed/legal-corpus.jsonl`.

| Hạng mục | Quy mô |
| --- | ---: |
| Văn bản nguồn | 52 |
| Structured nodes | 52.105 |
| Dung lượng JSONL đã xử lý | 93,37 MB |
| Quarantine records | 0 |

Phân bố node theo cấp pháp lý:

| Cấp | Số lượng |
| --- | ---: |
| `document` | 52 |
| `part` | 45 |
| `chapter` | 607 |
| `section` | 530 |
| `subsection` | 27 |
| `article` | 7.966 |
| `clause` | 24.571 |
| `point` | 18.307 |

Cấu trúc dữ liệu giữ lại quan hệ phân cấp của văn bản luật:

```text
document
  -> part
    -> chapter
      -> section/subsection
        -> article
          -> clause
            -> point
```

Mỗi dòng trong `legal-corpus.jsonl` là một node độc lập, có đủ thông tin để truy
vết nguồn, dựng citation và tái tạo quan hệ cha-con:

```json
{
  "law_id": "BLDS_2015",
  "level": "clause",
  "node_id": "BLDS_2015:article-1:clause-1",
  "parent_id": "BLDS_2015:article-1",
  "title": "Phạm vi điều chỉnh",
  "number": "1",
  "text": "...",
  "citation_label": "Khoản 1 Điều 1, Bộ luật Dân sự 2015",
  "source_url": "https://thuvienphapluat.vn/...",
  "hierarchy": {
    "part": "thứ nhất",
    "chapter": "I",
    "article": "1",
    "clause": "1",
    "point": null
  },
  "text_hash": "...",
  "schema_version": "1.0"
}
```

Trong pipeline retrieval, các node cấp `article`, `clause` và `point` là đơn vị
chính để embedding và truy xuất. PostgreSQL lưu metadata, nội dung văn bản và
quan hệ phân cấp; Qdrant lưu dense/sparse vectors để tìm kiếm hybrid. Khi trả
lời, backend lấy các node liên quan, rerank, dựng context theo hierarchy và hiển
thị citation từ `citation_label`/`source_url`.

## Công nghệ

| Lớp | Công nghệ |
| --- | --- |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, các service tương thích LangChain |
| Retrieval | Qdrant hybrid vector search, FAISS fallback cho local |
| Storage | PostgreSQL / Supabase |
| Models | Hugging Face embedding/reranker local, LLM provider từ xa |
| Deploy | Vercel cho frontend, Render/container host cho backend, Docker Compose local |

## Kiến trúc

```text
Người dùng
  |
  v
Next.js frontend
  - Giao diện chat
  - Màn hình tài liệu và quản trị
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
  +--> PostgreSQL: tài liệu, điều khoản, lịch sử chat
  +--> Qdrant: dense và sparse vectors
  +--> Local models hoặc remote inference providers
```

Thiết kế production được tách thành hai phần: Vercel phục vụ frontend, còn
FastAPI backend chạy trên container host như Render, Railway, Fly.io, Cloud Run,
ECS hoặc VPS. PostgreSQL có thể dùng Supabase, vector database có thể dùng
Qdrant Cloud.

## Cấu trúc thư mục

```text
.
├── backend/             # FastAPI app, RAG services, scripts, tests
├── frontend/            # Next.js app, components, API proxy routes
├── corpus/              # Corpus pháp luật đã xử lý, dùng khi ingest
├── docs/                # Ghi chú kỹ thuật và đánh giá
├── fine-tuning/         # Artifact huấn luyện embedding và reranker
├── models/              # Model local, không commit lên Git
├── docker-compose.yml   # Chạy full stack ở local
├── render.yaml          # Blueprint deploy backend trên Render
├── vercel.json          # Cấu hình build frontend trên Vercel
└── .env.example         # Mẫu biến môi trường
```

## Yêu cầu

- Docker Desktop
- Node.js 20 nếu chạy frontend trực tiếp
- Python 3.11 nếu chạy backend trực tiếp
- PostgreSQL hoặc Supabase
- Qdrant local hoặc Qdrant Cloud
- API key của provider sinh câu trả lời, cấu hình ở backend
- NVIDIA GPU nếu muốn tăng tốc embedding và ingest ở local

## Cấu hình môi trường

Tạo file môi trường local:

```powershell
Copy-Item .env.example .env
```

Cập nhật các giá trị deploy trong `.env` và không commit file này lên Git.

| Biến | Mục đích |
| --- | --- |
| `APP_URL` | URL frontend public được backend cho phép. |
| `BACKEND_URL` | URL backend mà frontend API proxy sử dụng. |
| `CHAT_STORAGE_MODE` | `postgres` cho lịch sử dùng chung hoặc `browser` cho lịch sử trong trình duyệt. |
| `STORAGE_BACKEND` | `qdrant_postgres` cho đường lưu trữ retrieval production. |
| `POSTGRES_DSN` | Chuỗi kết nối PostgreSQL. Với Supabase nên dùng `sslmode=require`. |
| `QDRANT_URL` | Endpoint Qdrant. |
| `QDRANT_API_KEY` | API key Qdrant Cloud. Để trống nếu dùng Qdrant local. |
| `QDRANT_COLLECTION` | Collection điều khoản pháp luật đang dùng. |
| `GOOGLE_API_KEY` | Google AI Studio key cho luồng sinh câu trả lời tương thích Gemini. |
| `HUGGINGFACE_API_KEY` | Hugging Face token cho truy cập model từ xa. |
| `HUGGINGFACE_EMBEDDING_MODEL` | Đường dẫn embedding local hoặc remote model ID. |
| `RERANKER_MODEL` | Đường dẫn cross-encoder reranker local. |
| `EMBEDDING_DEVICE` | `cpu` hoặc `cuda`. |

Đường dẫn model thường dùng khi chạy Docker local:

```env
HUGGINGFACE_EMBEDDING_MODEL=/models/embedding/vietlaw-bge-m3-finetuned/best
RERANKER_MODEL=/models/reranking/vietlaw-bge-reranker-v2-m3-finetuned/checkpoint-3306
```

## Chạy local

Khởi động full stack:

```powershell
docker compose up --build
```

Mở ứng dụng:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

Chạy từng service khi cần:

```powershell
docker compose up backend
docker compose up frontend
```

Chạy frontend trực tiếp:

```powershell
cd frontend
npm install
npm run dev
```

Khi chạy frontend trực tiếp, đặt:

```env
BACKEND_URL=http://localhost:8000
```

## Ingest dữ liệu

Backend không tự ingest khi khởi động. Chạy lệnh sau để nạp hoặc tiếp tục nạp
corpus:

```powershell
docker compose --profile tools run --rm ingest
```

Script ingest đọc `corpus/processed/legal-corpus.jsonl`, ghi tài liệu và điều
khoản vào PostgreSQL, embed các điều khoản còn thiếu, upsert vector vào Qdrant
và kiểm tra số lượng bản ghi/vector cuối cùng.

## Deploy

### Frontend: Vercel

Deploy thư mục `frontend/` làm project root trên Vercel. File `vercel.json` đã
được cấu hình theo layout này.

Cấu hình khuyến nghị:

```text
Framework preset: Next.js
Install command: npm ci
Build command: npm run build
Output directory: .next
Root directory: frontend
```

Chỉ đặt các biến an toàn cho frontend trên Vercel:

```env
BACKEND_URL=https://your-backend.example.com
NEXT_PUBLIC_CHAT_STORAGE_MODE=browser
```

### Backend: Render hoặc container host

`render.yaml` khai báo backend FastAPI dưới dạng Docker web service, dùng
`/health` làm health check path.

Các biến backend cần có:

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

Giữ secret của PostgreSQL, Qdrant, Google, Hugging Face và OpenAI ở backend
host; không đưa các giá trị này vào biến public phía frontend.

## Kiểm tra

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

Trước khi chia sẻ bản deploy, hãy kiểm tra frontend gọi được `BACKEND_URL`,
backend health check thành công, và số lượng bản ghi trong PostgreSQL/Qdrant
khớp với corpus đã xử lý.
