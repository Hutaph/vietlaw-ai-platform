# VietLaw AI - Hệ thống Hỏi đáp Pháp luật Việt Nam

Chatbot tra cứu pháp luật Việt Nam sử dụng kỹ thuật **RAG (Retrieval-Augmented Generation)**.
Hệ thống tách dữ liệu pháp luật thành các điều khoản, lập chỉ mục dense/sparse trong Qdrant, truy xuất các căn cứ liên quan và dùng Gemini hoặc provider từ xa được cấu hình để sinh câu trả lời tiếng Việt có citation.

> **Lưu ý pháp lý:** Đây là hệ thống phục vụ nghiên cứu/đồ án sinh viên, không phải dịch vụ tư vấn pháp lý chuyên nghiệp. Người dùng cần kiểm tra lại văn bản pháp luật chính thức hoặc hỏi chuyên gia trước khi ra quyết định.

Luồng triển khai chính dùng **PostgreSQL + Qdrant**. FAISS vẫn được hỗ trợ cho chạy local hoặc fallback legacy khi được bật tường minh, nhưng quality runtime mặc định không tự fallback sang index cũ.

![Sơ đồ pipeline RAG của VietLaw AI](overview.png)

> **Project môn học:** Introduction to Machine Learning

## Danh sách thành viên

| Mã số sinh viên | Họ tên |
|---|---|
| 23120283 | Phạm Quốc Khánh |
| 23120301 | Phạm Thành Nam |
| 23120318 | Trương Quang Phát |
| 23120329 | Châu Huỳnh Phúc (Trưởng nhóm) |
| 23120334 | Huỳnh Tấn Phước |

---

## Mục lục

- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Hướng dẫn cài đặt và chạy](#hướng-dẫn-cài-đặt-và-chạy)
- [Kỹ thuật sử dụng](#kỹ-thuật-sử-dụng)
- [Tính năng](#tính-năng)
- [Đánh giá chất lượng](#đánh-giá-chất-lượng)
- [Dữ liệu pháp luật](#dữ-liệu-pháp-luật)
- [Fine-tuning và đánh giá](#fine-tuning-và-đánh-giá)
- [Công nghệ](#công-nghệ)
- [Kiểm thử](#kiểm-thử)
- [Hạn chế đã biết](#hạn-chế-đã-biết)
- [Tích hợp mô hình cục bộ](docs/local_model_integration.md)

---

## Kiến trúc hệ thống

Hệ thống theo mô hình **Client-Server** với 2 thành phần chính giao tiếp qua REST API:

```text
  NGƯỜI DÙNG
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 15)                  │
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Sidebar  │  │ChatInterface │  │ ProviderSelector │   │
│  │(lịch sử) │  │  (giao diện) │  │  (chọn model)    │   │
│  └──────────┘  └──────┬───────┘  └──────────────────┘   │
│                       │                                 │
│               POST /api/chat                            │
│               ┌───────▼────────┐                        │
│               │ API Route Proxy│ ← Next.js API Route    │
│               └───────┬────────┘                        │
└───────────────────────┼─────────────────────────────────┘
                        │ HTTP POST (JSON)
┌───────────────────────▼─────────────────────────────────┐
│                 BACKEND (FastAPI + Python)              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ app/api/chat.py          → Xử lý request        │    │
│  │ app/services/pipeline.py → RAG Orchestrator     │    │
│  │ app/services/search/     → FAISS, BM25, Hybrid  │    │
│  │ app/services/reranking/  → CrossEncoder         │    │
│  │ app/config.py            → Cấu hình pipeline     │    │
│  └─────────────────────────────────────────────────┘    │
│       │                                                 │
│       │ Local fine-tuned embedding + Qdrant Cloud       │
│       ▼                                                 │
│  ┌─────────────────────────────────────────────┐        │
│  │ Embedding: fine-tuned BGE-M3 local artifact │        │
│  │ Retrieval: Qdrant dense/sparse hybrid search│        │
│  │ Reranker: fine-tuned local cross-encoder    │        │
│  │ LLM: Gemini / configured remote provider    │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### Luồng xử lý chính

1. **Người dùng** nhập câu hỏi pháp lý → Frontend gửi `POST /api/chat`
2. **Next.js API Route** (proxy) chuyển tiếp request đến Backend FastAPI
3. **Backend** tạo embedding bằng fine-tuned local embedding model
4. **Qdrant** chạy dense/sparse hybrid retrieval với RRF để lấy các nguồn ứng viên
5. Fine-tuned local **Cross-Encoder reranker** xếp hạng lại tối đa 10 nguồn ứng viên
6. Context builder tuần tự hóa 5 nguồn được chọn cuối cùng, kèm source ID và metadata pháp lý
7. Gemini hoặc provider từ xa sinh câu trả lời; backend kiểm tra các citation ID dựa trên final context
8. Backend trả `{text, contextUsed}` hoặc SSE `done`; câu trả lời tổng hợp cuối cùng và câu trả lời được lưu đều dùng bản citation đã được làm sạch.
9. Tác vụ nền cập nhật phần tóm tắt bộ nhớ hội thoại sau khi lượt chat đã hoàn tất và được lưu.

Cấu hình runtime mặc định:

- `candidateK=10`
- số nguồn đưa vào reranker tối đa 10
- final `topK=5`
- dense/sparse prefetch multiplier thông thường = 2
- truy vấn có citation rõ ràng dạng `Điều`/`Khoản`/`Điểm` dùng internal prefetch multiplier = 4
- prefetch mở rộng chỉ tăng recall trước fusion, không tăng workload của reranker hoặc final topK

Tài liệu chi tiết:

- [Đo độ trễ pipeline](docs/pipeline_latency_measurement.md)
- [Đánh giá chất lượng câu trả lời pháp luật](docs/legal_answer_quality_evaluation.md)
- [Tích hợp mô hình cục bộ](docs/local_model_integration.md)

### Hai pipeline dữ liệu

```text
INGESTION
data/processed/*.json
  → load Knowledge Base
  → ClauseChunker
  → dense embedding bằng fine-tuned local artifact + sparse BM25 vector
  → PostgreSQL (law/clause metadata, content)
  → Qdrant (text-dense, text-sparse, payload)

ONLINE QA
question
  → route theo cấu hình runtime
  → Qdrant hybrid search + RRF (hoặc FAISS fallback nếu bật)
  → deduplicate → local cross-encoder reranking
  → NestedContextBuilder + token budget
  → LLM → citation filtering → stream/JSON response
```

Ingestion không nên chạy lại ở mỗi lần khởi động. Với Docker, backend đặt
`DISABLE_AUTO_INGEST=true` và việc nạp dữ liệu được thực hiện bằng service `ingest`.

---

## Cấu trúc dự án

```text
Vietnam-Legal-QA-System/
│
├── .env.example                 # Mẫu biến môi trường
├── .gitignore                   # Quy tắc Git ignore
├── README.md                    # Tài liệu dự án (file này)
├── docker-compose.yml           # Docker Compose cho phát triển
│
├── backend/                     # === BACKEND (Python + FastAPI) ===
│   ├── main.py                  # Điểm vào — chạy: python main.py
│   ├── rag_service.py           # Shim tương thích ngược
│   ├── requirements.txt         # Dependencies Python
│   ├── embedded_files.json      # Theo dõi các file đã embedding
│   │
│   ├── app/                     # Package chính (modular)
│   │   ├── __init__.py
│   │   ├── main.py              # Tạo FastAPI app + sự kiện startup
│   │   ├── config.py            # Cấu hình tập trung (paths, API keys, constants)
│   │   ├── models.py            # Pydantic schema (ChatRequest, ChatResponse)
│   │   │
│   │   ├── api/                 # Lớp API
│   │   │   └── chat.py          # Router POST /chat — xử lý request/response
│   │   │
│   │   ├── services/            # Lớp business logic
│   │   │   ├── pipeline.py      # Orchestrator kết nối các module
│   │   │   ├── storage.py       # Quản lý Database (PostgreSQL + Qdrant)
│   │   │   ├── knowledge_base.py# Fallback KB trong bộ nhớ
│   │   │   ├── llm.py           # Kết nối LLM + System Prompt
│   │   │   ├── search/          # Module search: Qdrant, FAISS fallback
│   │   │   ├── reranking/       # Module reranking: NoRerank, CrossEncoder
│   │   │   ├── context_builder/ # Xây dựng context dạng nested 2 cấp
│   │   │   ├── chunking/        # Chia tài liệu theo clause
│   │   │   ├── sparse_vector.py # Sinh Sparse Vectors cho BM25 (TF) tiếng Việt
│   │   │   └── embedding/       # Fine-tuned local text embedding
│   │   │
│   │   └── utils/               # Tiện ích dùng chung
│   │       └── logging.py       # Logging chuẩn
│   │
│   ├── data/
│   │   ├── processed/           # 9 JSON: 8 bộ luật chính + dữ liệu mẫu
│   │   └── raw/                 # Dữ liệu thô (chưa có)
│   │
│   └── vietlaw_faiss_index/     # FAISS index local/fallback (nếu có)
│       ├── index.faiss          # Dữ liệu vector
│       └── index.pkl            # Metadata
│
├── frontend/                    # === FRONTEND (Next.js 15 + React 19) ===
│   ├── package.json             # Dependencies Node.js
│   ├── next.config.ts           # Cấu hình Next.js
│   ├── tsconfig.json            # Cấu hình TypeScript
│   ├── postcss.config.mjs       # PostCSS + TailwindCSS
│   │
│   ├── app/                     # Next.js App Router
│   │   ├── layout.tsx           # Root layout (metadata, style toàn cục)
│   │   ├── page.tsx             # Trang chính — render ChatInterface
│   │   ├── globals.css          # CSS toàn cục + scrollbar tùy chỉnh
│   │   └── api/chat/
│   │       └── route.ts         # API Route Proxy → chuyển tiếp đến Backend
│   │
│   ├── components/              # React components
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx    # Giao diện chat chính
│   │   │   ├── ChatMessage.tsx      # Hiển thị tin nhắn + căn cứ pháp lý
│   │   │   ├── ProviderSelector.tsx # Dropdown chọn model AI
│   │   │   └── Sidebar.tsx          # Sidebar quản lý phiên chat
│   │   └── ui/
│   │       └── LoadingSpinner.tsx   # Animation loading khi chờ LLM
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── use-chat-sessions.ts # Quản lý sessions
│   │   ├── use-click-outside.ts # Đóng dropdown khi click ngoài
│   │   └── use-mobile.ts        # Phát hiện thiết bị mobile
│   │
│   └── lib/                     # Tiện ích dùng chung
│       ├── types.ts             # Interface TypeScript
│       ├── constants.ts         # Hằng số (models, categories, storage keys)
│       └── utils.ts             # Hàm tiện ích (gộp class)
│
├── fine-tuning/                 # Fine-tune embedding/reranker và artifact đánh giá
│   ├── embedding/notebooks/
│   └── reranking/notebooks/
└── backend/evaluation/          # Chuẩn bị dataset và đánh giá Ragas
```

### Giải thích thiết kế

| Layer | Vai trò | Files |
|---|---|---|
| **API Layer** | Nhận HTTP request, validate và trả response | `api/chat.py`, `models.py` |
| **Service Layer** | Xử lý business logic: RAG, LLM, Vector DB | `services/llm.py`, `pipeline.py`, `storage.py` |
| **Config Layer** | Quản lý cấu hình, env và paths | `config.py` |
| **Utils Layer** | Tiện ích dùng chung | `utils/logging.py` |

> **Nguyên tắc:** Mỗi file **một nhiệm vụ duy nhất** (Single Responsibility). API layer không chứa business logic, service layer không biết về HTTP.

---

## Hướng dẫn cài đặt và chạy

### Yêu cầu hệ thống

| Yêu cầu | Phiên bản |
|---|---|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Google/OpenAI-compatible LLM key | Dùng cho phần sinh câu trả lời từ provider remote |

`requirements.txt` hỗ trợ embedding qua HuggingFace API. Nếu muốn chạy embedding
local với `HUGGINGFACE_EMBEDDING_MODE=local`, cần cài thêm `sentence-transformers`
và PyTorch; Dockerfile đã cài sẵn các gói này.

### Bước 1: Clone và cấu hình

```bash
# Clone repository
git clone https://github.com/cyhapun/Vietnam-Legal-QA-System.git
cd Vietnam-Legal-QA-System

# Tạo file biến môi trường từ template
cp .env.example .env

# .env chứa cấu hình mặc định của server và hạ tầng.
# API key của provider/model khi chạy runtime được cấu hình trong giao diện web.
#
# Query embedding được tạo bằng fine-tuned local model để bảo đảm
# đồng nhất với không gian embedding của dữ liệu đã index:
# EMBEDDING_PROVIDER=huggingface
# HUGGINGFACE_EMBEDDING_MODE=local
# HUGGINGFACE_EMBEDDING_MODEL=../models/embedding/vietlaw-bge-m3-finetuned/best
# HUGGINGFACE_API_KEY có thể để trống khi dùng embedding/reranking cục bộ.
#
# PostgreSQL chạy local; Qdrant có thể dùng Qdrant Cloud nếu collection
# đã được tạo bằng cùng fine-tuned embedding model:
# STORAGE_BACKEND=qdrant_postgres
# POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
# QDRANT_URL=http://localhost:6333
#
# Khi chạy bằng Docker Compose, dùng hostname nội bộ:
# POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/vietlaw
# QDRANT_URL=http://qdrant:6333
#
# Cấu hình fallback tùy chọn ở server:
# GOOGLE_API_KEY=
# ENABLE_GOOGLE_FALLBACK=false
# INFERENCE_STRATEGY=remote_first
# remote_first không tự fallback sang Ollama local.
```

### Bước 2: Chạy Backend (Terminal 1)

```bash
# Di chuyển vào thư mục backend
cd backend

# Tạo virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

# Cài đặt dependencies
python -m pip install -r requirements.txt
python -m pip install -r requirements-local.txt  # local/Docker fine-tuned models

# Khởi chạy server
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
# Server chạy tại: http://localhost:8000
```

### Bước 2a: Chạy với PostgreSQL + Qdrant

```bash
# Từ thư mục root project
docker compose up -d postgres qdrant

# Trong backend, dùng storage backend dựa trên database
# .env
# STORAGE_BACKEND=qdrant_postgres
# POSTGRES_DSN=postgresql://postgres:postgres@localhost:15432/vietlaw
# QDRANT_URL=http://localhost:6333

# Chỉ chạy ingestion thủ công khi bạn đang xây dựng local collection mới.
# Không chạy ingestion/re-index vào Qdrant Cloud đã có dữ liệu production.
# Chạy từ thư mục backend.
cd backend
python scripts/ingest_to_storage.py
```

> Nếu dịch vụ database chưa sẵn sàng, `/readiness` sẽ trả `503` cho đến khi PostgreSQL, Qdrant và local models sẵn sàng. FAISS fallback đang tắt mặc định để tránh truy vấn index cũ ngoài ý muốn.
> **Lưu ý quan trọng:** Phải chạy từ **thư mục `backend/`**, không phải từ thư mục root!

### Bước 3: Chạy Frontend (Terminal 2)

```bash
# Mở terminal MỚI, di chuyển vào thư mục frontend
cd frontend

# Cài đặt dependencies
npm install

# Khởi chạy dev server
npm run dev
# Mở trình duyệt tại: http://localhost:3000
```

### Chạy toàn bộ bằng Docker

```bash
# Từ thư mục root project; backend cố ý không auto-ingest
docker compose up --build -d

# Nạp dữ liệu sau khi PostgreSQL và Qdrant đã sẵn sàng
docker compose --profile tools run --rm ingest

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

Khi chạy toàn bộ bằng Docker, `.env` phải dùng hostname nội bộ:

```dotenv
POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/vietlaw
QDRANT_URL=http://qdrant:6333
```

### Lưu ý khi chạy

- **Backend phải chạy TRƯỚC Frontend** — Frontend proxy request đến Backend.
- **Runtime chính** dùng PostgreSQL + Qdrant. FAISS chỉ là fallback kế thừa và đang tắt mặc định.
- **Lần đầu khởi động** với preload/warm-up local models có thể mất khoảng 80-90 giây trên CPU baseline.
- Khi bật `STORAGE_BACKEND=qdrant_postgres`, backend kiểm tra PostgreSQL và Qdrant trong `/readiness`.
- Khi dùng FAISS, backend tải index local và dùng Knowledge Base trong RAM để dựng context.
- Khi dùng `qdrant_postgres`, startup kiểm tra schema PostgreSQL và collection Qdrant.
- Docker backend đặt `DISABLE_AUTO_INGEST=true`; không tự ingest/re-index vào collection đã tồn tại.
- Để nạp dữ liệu ban đầu hoặc re-embed dữ liệu mới, chạy `python scripts/ingest_to_storage.py`
  từ `backend/`, hoặc chạy service `ingest` trong Docker Compose.
- Nếu Qdrant không truy cập được, backend chỉ fallback sang FAISS khi `ENABLE_FAISS_FALLBACK=true`.
  Lỗi embedding, Qdrant auth/schema hoặc thiếu collection được trả rõ để tránh truy vấn bằng vector space khác.

### Biến môi trường quan trọng

Không commit file `.env`. Các nhóm biến chính:

- Runtime: `POSTGRES_DSN`, `QDRANT_URL`, `QDRANT_API_KEY`, `QDRANT_COLLECTION`, provider API keys.
- Local models: `HUGGINGFACE_EMBEDDING_MODEL`, `RERANKER_MODEL`, `EMBEDDING_DIMENSION=1024`.
- Retrieval: `RETRIEVER_CANDIDATE_K=10`, `RERANKER_MAX_CANDIDATES=10`, final `topK` mặc định là 5 trong request schema.
- Startup: `LOCAL_MODELS_PRELOAD_ENABLED=true`, `LOCAL_MODELS_WARMUP_ENABLED=true`.
- Observability: `PIPELINE_TIMING_ENABLED=false` mặc định.

Preload/warm-up giúp request đầu tiên ổn định hơn nhưng làm `/readiness` lâu hơn. Với CPU baseline, cấu hình deployment nên đặt startup/readiness timeout lớn hơn 120 giây.

### Health và readiness

- `GET /health`: liveness của process, trả nhanh và không chờ model/dependency.
- `GET /readiness`: chỉ ready khi config, PostgreSQL, Qdrant, local model artifacts và preload/warm-up đã sẵn sàng.

---

## Kỹ thuật sử dụng

### 1. RAG (Retrieval-Augmented Generation)

Kỹ thuật cốt lõi của hệ thống — **kết hợp truy xuất thông tin + sinh văn bản**:

```text
Câu hỏi → [Retriever] → Điều khoản liên quan → [LLM] → Câu trả lời có trích dẫn
```

**Tại sao dùng RAG?** LLM đơn thuần có thể tạo ra thông tin pháp lý không chính xác. RAG giúp ràng buộc câu trả lời vào nguồn đã truy xuất và làm citation dễ kiểm chứng hơn, nhưng không bảo đảm độ chính xác tuyệt đối.

### 2. Tìm kiếm hybrid trên Qdrant (Native Sparse Vectors)

Hệ thống sử dụng cơ sở dữ liệu vector tiên tiến (Qdrant) để thực hiện tìm kiếm kết hợp:
- **Dense Vector Search**: Semantic search qua fine-tuned BGE-M3 embedding local (1024 chiều), truy vấn collection Qdrant đã index cùng embedding space.
- **Sparse Vector Search (BM25)**: Tìm kiếm từ khóa chính xác (Exact Keyword Match) thông qua thuật toán sinh vector thưa tự xây dựng cho tiếng Việt.
- **Reciprocal Rank Fusion (RRF)**: Qdrant nhận các truy vấn dense/sparse qua nhiều khối `prefetch`; backend dùng `query_batch_points` và hợp nhất thứ hạng bằng RRF để tương thích với các phiên bản Qdrant khác nhau.
- *(Dự phòng: Vẫn hỗ trợ FAISS cục bộ cho hệ thống không có Qdrant)*.

### 3. Reranking bằng Cross-Encoder

Sau bước Search, kết quả có thể được xếp hạng lại (Reranking) để cải thiện mức liên quan của final context:
- **CrossEncoderReranker**: Dùng fine-tuned BGE reranker local để đánh giá chi tiết (joint encoding) giữa Query và Document.
- Có thể bật/tắt dễ dàng qua config `PIPELINE_RERANKING=cross_encoder|none`.

### 4. Fallback FAISS/MMR kế thừa

FAISS/MMR vẫn tồn tại cho môi trường phát triển cũ, nhưng runtime chính của quality branch là Qdrant hybrid retrieval. `ENABLE_FAISS_FALLBACK=false` theo mặc định để tránh âm thầm dùng index không cùng embedding space.

### 5. Xây dựng nested context (dẫn chiếu 2 cấp)

Tính năng nổi bật — xây dựng **context đệ quy** giúp LLM hiểu liên kết giữa các điều luật:

```text
[Cấp 0] Điều khoản được retrieve → Hiển thị đầy đủ nội dung
   └── [Cấp 1] Dẫn chiếu từ Cấp 0 → Lấy toàn bộ content từ RAM
          └── [Cấp 2] Dẫn chiếu từ Cấp 1 → Chỉ lấy tóm tắt
```

**Ví dụ:** Điều 137 Luật Đất đai dẫn chiếu đến Điều 45 → hệ thống tự động lấy nội dung Điều 45 đưa vào context cho LLM.

### 6. Lọc theo lĩnh vực pháp luật

Lọc kết quả truy xuất theo **lĩnh vực pháp luật** để thu hẹp phạm vi tìm kiếm:

- Tất cả các luật
- Dân sự
- Gia đình & Nhân thân
- Đất đai
- Bất động sản
- Xây dựng & Môi trường
- Giao thông
- Trật tự & Xử phạt

Metadata `law_id` và `category` được dùng để lọc document trước khi tìm kiếm.
Mỗi lựa chọn trên giao diện có thêm mô tả ngắn về phạm vi pháp luật tương ứng.

### 7. Grounding câu trả lời và kiểm tra citation

Prompt yêu cầu LLM trả lời bằng tiếng Việt, dựa trên context được cung cấp và dùng source ID hợp lệ. Sau khi model sinh câu trả lời, backend kiểm tra các citation ID theo final context:

- citation ID có trong final context được giữ;
- citation ID không tồn tại trong final context bị loại khỏi câu trả lời tổng hợp cuối cùng;
- câu trả lời được lưu và lịch sử hội thoại dùng bản đã được làm sạch;
- nếu một answer pháp lý chỉ còn citation không hợp lệ, backend dùng fallback thiếu căn cứ ngắn gọn.

Với SSE streaming, các token chunk có thể đã được phát trước bước kiểm tra cuối cùng. Sự kiện `done`, câu trả lời tổng hợp cuối cùng và câu trả lời được lưu đều dùng bản đã được làm sạch; các token chunk đã phát trước đó không thể được thu hồi.

### 8. Cơ sở dữ liệu lưu trữ lâu dài (Qdrant & PostgreSQL)

Thay vì tải toàn bộ index vào RAM, phiên bản mới nhất sử dụng kiến trúc lưu trữ vĩnh viễn:
- **PostgreSQL**: Lưu trữ metadata và nội dung nguyên bản của văn bản pháp luật, trạng thái ingest.
- **Qdrant**: Lưu trữ Named Vectors (`text-dense`, `text-sparse`) cho Hybrid Search hiệu suất cao.

Đảm bảo hệ thống có thể mở rộng lên hàng triệu điều luật mà không gây tràn bộ nhớ (OOM). Khởi động siêu tốc vì bỏ qua việc rebuild BM25 Index.

### Lưu phiên chat và hành vi khi tải lại trang

- `chat_sessions` và `chat_messages` được lưu trong PostgreSQL; bộ nhớ trình duyệt chỉ lưu ID phiên đang hoạt động và cache để phục hồi giao diện nhanh.
- Lần truy cập đầu tiên khi chưa có phiên hoạt động sẽ mở khung chat mới trống; phiên này chưa được lưu cho đến khi người dùng gửi tin nhắn.
- Khi tải lại trang trong một cuộc trò chuyện đã tồn tại, frontend khôi phục đúng phiên đó và giữ các tin nhắn tiếp theo dưới cùng `sessionId`.
- Các cuộc trò chuyện cũ được lazy-load từ PostgreSQL khi người dùng chọn trong sidebar.
- Nếu cache trong trình duyệt bị cũ, frontend đối chiếu lại với PostgreSQL khi `/chat/sessions` trả về `message_count` lớn hơn.
- Backend lưu đầy đủ lượt `user/assistant` trước khi trả `/chat` hoặc phát SSE `/chat/stream` `done`, nên tải lại trang ngay sau đó vẫn hiển thị cả câu hỏi và câu trả lời.

### 9. Chính sách suy luận hybrid

Hệ thống dùng biến môi trường `INFERENCE_STRATEGY` để chọn thứ tự provider:
- `remote_first`: chỉ dùng provider remote và các remote fallback đã cấu hình; không khởi tạo hoặc fallback sang Ollama local.
- `local_first`: dùng Ollama local trước, sau đó mới fallback sang provider remote nếu cấu hình cho phép.

Các lớp chính:
- **LLM Layer**: trong `remote_first`, backend dùng runtime/provider từ xa và Google fallback nếu được bật; trong `local_first`, Ollama được dùng trước.
- **Embedding Layer**: với `HUGGINGFACE_EMBEDDING_MODE=local`, retrieval dùng fine-tuned embedding artifact trên filesystem. Lỗi artifact, dimension, Qdrant auth/schema hoặc thiếu collection được báo rõ; backend không fallback sang Hugging Face embedding API hoặc FAISS trừ khi được bật tường minh.
- **Reranking Layer**: với `PIPELINE_RERANKING=cross_encoder`, backend dùng fine-tuned Cross-Encoder cục bộ từ `RERANKER_MODEL`. Nếu artifact lỗi, request fail rõ hoặc fail-open theo `RERANKER_FAIL_OPEN`; không fallback sang Hugging Face reranking API.

### 10. Quản lý bộ nhớ hội thoại lai

Để tránh hiện tượng tràn ngữ cảnh (Context Bloat) và suy giảm độ tập trung của LLM khi cuộc hội thoại kéo dài:
- **Tóm tắt tịnh tiến (Incremental Summarization):** Chạy ngầm một model nhẹ (ví dụ `qwen2.5:1.5b`) thông qua `asyncio.create_task` ngay sau khi trả lời xong để nén các lượt chat cũ thành một đoạn tóm tắt ngắn gọn.
- **Trí nhớ lai (Sliding Window Context):** Khi tạo Prompt cho LLM sinh câu trả lời, hệ thống kết hợp `[Tóm tắt bối cảnh từ PostgreSQL]` + `[4 tin nhắn nguyên bản gần nhất]`.
Kỹ thuật này giúp tiết kiệm lượng lớn token API, giảm thiểu độ trễ (latency) mà người dùng vẫn cảm nhận mạch hội thoại được duy trì trơn tru.

---

## Fine-tuning và đánh giá

Thư mục `fine-tuning/` chứa các notebook cho hai hướng thử nghiệm:

- `embedding/`: sinh dữ liệu query–điều khoản, fine-tune bi-encoder và so sánh embedding.
- `reranking/`: tạo hard negatives, fine-tune cross-encoder và đánh giá reranker.

Đánh giá end-to-end nằm trong `backend/evaluation/`. Dataset được chuẩn bị từ
`VLSP2025-LegalSML`, sau đó script gọi API `/chat` và tính các metric Ragas:
`context_precision`, `context_recall`, `faithfulness` và `answer_relevancy`.

```bash
cd backend
pip install -r evaluation/requirements.txt
python evaluation/prepare_dataset.py
python evaluation/evaluate.py
```

Backend phải đang chạy tại `http://localhost:8000`; kết quả chi tiết được ghi vào
`backend/evaluation/results.csv`.

---

## Tính năng

### Chatbot Pháp luật
- **Hỏi đáp pháp lý** bằng ngôn ngữ tự nhiên tiếng Việt.
- **Trích dẫn căn cứ pháp lý** — mỗi câu trả lời kèm nguồn điều khoản cụ thể.
- **Dẫn chiếu chéo tự động** — hệ thống tự tìm và đính kèm các điều luật liên quan.
- **Lọc theo lĩnh vực** — chọn chuyên ngành luật để thu hẹp phạm vi truy xuất.

### Đa model AI
- **Provider/model BYOK**: Google Gemini, HuggingFace Router và Ollama local theo catalog trong frontend.
- **Model mặc định**: Gemini 3.1 Flash-Lite.
- **Chuyển đổi model** ngay trong giao diện để so sánh hành vi trả lời trên cùng pipeline retrieval.
- Danh sách model/provider hợp lệ được kiểm soát trong `provider_registry.py` và catalog frontend.

### Giao diện hiện đại
- **UI chuyên nghiệp** — thiết kế tối giản, responsive, animations mượt.
- **Sidebar quản lý phiên chat** — tạo mới, chọn, xóa các cuộc hội thoại.
- **Lưu lịch sử đồng bộ** lên cơ sở dữ liệu PostgreSQL — mỗi lượt chat được lưu đủ `user/assistant` trước khi hoàn tất, hỗ trợ refresh an toàn và duy trì trí nhớ dài hạn.
- **Phím tắt** — Enter gửi, Shift+Enter xuống dòng.
- **Render Markdown** — câu trả lời hiển thị với format (heading, bold, list...).

### Pipeline dữ liệu và đánh giá
- **Kiến trúc Modular** — Pipeline tách biệt thành Embedding, Search, Reranking, ContextBuilder và Answer Generation.
- **Công cụ đánh giá chất lượng** — có retrieval fixture, insufficient-context fixture, evaluator theo từng stage và rubric đánh giá thủ công.
- **Embedding incremental** — chỉ embed file mới, bỏ qua file đã xử lý.
- **Ablation Study** — Thay đổi thuật toán Search/Rerank linh hoạt bằng cấu hình `.env` trong phạm vi mode được code hỗ trợ.
- **Ingestion idempotent** — bỏ qua khi database đã có đủ điều khoản; chạy lại script khi thêm/sửa dữ liệu để upsert và invalidate cache.
- **Dữ liệu** — 5.756 điều khoản và 843 dẫn chiếu chéo từ 8 bộ luật chính; thư mục hiện có thêm một JSON mẫu kiểm thử.

---

## Đánh giá chất lượng

Hệ thống hiện có bộ công cụ đánh giá tự động cho retrieval, citation và các trường hợp không đủ căn cứ. Phạm vi hiện tại gồm:

- bộ fixture retrieval pháp luật gồm 20 bản ghi: `backend/tests/fixtures/legal_retrieval_quality.jsonl`
- bộ fixture gồm 4 trường hợp không đủ ngữ cảnh: `backend/tests/fixtures/legal_insufficient_context_quality.jsonl`
- công cụ đánh giá tự động: `backend/scripts/evaluate_legal_quality.py`
- các metric xác định về nguồn/citation và một đợt đánh giá thủ công nhỏ.

Ví dụ chạy retrieval evaluation từ `backend/`:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_retrieval_quality.jsonl \
  --retrieval-only \
  --candidate-k 10 \
  --top-k 5 \
  --output /tmp/vietlaw-quality-evaluation.json
```

Ví dụ chạy insufficient-context answer evaluation khi backend đã ready:

```bash
.venv/bin/python scripts/evaluate_legal_quality.py \
  --dataset tests/fixtures/legal_insufficient_context_quality.jsonl \
  --answer-evaluation \
  --base-url http://127.0.0.1:8000 \
  --candidate-k 10 \
  --top-k 5 \
  --output /tmp/vietlaw-insufficient-context-evaluation.json
```

Các report được sinh ra nên đặt ngoài repository, ví dụ `/tmp`.

### Kết quả đánh giá trên bộ dữ liệu kiểm thử

Đánh giá retrieval trên 20 bản ghi fixture:

| Metric | Kết quả |
|---|---:|
| Retrieval Hit@10 | 1.00 |
| Retrieval Recall@10 | 1.00 |
| Reranker Hit@5 | 1.00 |
| Reranker Recall@5 | 1.00 |
| MRR@10 | 0.6108 |
| Critical retrieval misses | 0 |
| Empty contexts | 0 |
| Duplicate contexts | 0 |

Đánh giá câu trả lời:

| Metric | Kết quả |
|---|---:|
| Số request câu trả lời được đánh giá | 16 |
| Required citation presence | 0.9375 |
| Invalid citations in final answer | 0 |
| Unused-by-answer | 0 |
| Unsupported detector findings in final regular answer set | 0 |

Đánh giá trường hợp không đủ ngữ cảnh:

| Metric | Kết quả |
|---|---:|
| Số bản ghi fixture | 4 |
| Số lần chạy service-level | 8 |
| Safe fallback or cautious guidance | 8/8 |
| Invented citations returned | 0 |
| Overconfident outputs | 0 |

Đánh giá thủ công:

| Metric | Kết quả |
|---|---:|
| Số câu trả lời được review | 18 |
| Score 0 | 0 |
| Score 1 | 1 |
| Score 2 | 17 |
| Average score | 1.94/2 |

Các số liệu trên chỉ phản ánh kết quả trên các bộ fixture nhỏ hiện tại và không được hiểu là độ chính xác pháp lý tổng quát của toàn hệ thống.

---

## Dữ liệu pháp luật

| # | Văn bản pháp luật | Số điều khoản | Dẫn chiếu |
|---|---|---|---|
| 1 | Luật Đất đai 2024 | 1.272 | 201 |
| 2 | Bộ luật Tố tụng Dân sự 2025 | 1.523 | 225 |
| 3 | Luật Bảo vệ Môi trường 2025 | 835 | 49 |
| 4 | Luật Nhà ở 2025 | 790 | 211 |
| 5 | Luật Xây dựng 2025 | 566 | 42 |
| 6 | Luật Kinh doanh BĐS 2025 | 349 | 53 |
| 7 | Luật Công chứng 2026 | 287 | 48 |
| 8 | Luật Tương trợ Tư pháp HS 2025 | 134 | 14 |
| | **Tổng cộng** | **5.756** | **843** |

### Schema dữ liệu

Mỗi file JSON trong `data/processed/` có cấu trúc:

```json
{
  "law_info": {
    "law_id": "LDD_2024",
    "law_name": "Luật Đất đai 2024",
    "publisher": "Quốc hội",
    "document_number": "45/VBHN/VPQH/2025",
    "effective_date": "...",
    "executive_summary": "Tóm tắt nội dung..."
  },
  "clauses": [
    {
      "id": "LDD_2024_D10_K1",
      "position": {
        "chapter": 1,
        "article": 10,
        "article_title": "Phân loại đất",
        "clause": 1
      },
      "content": "Nội dung điều khoản...",
      "cross_references": [
        {
          "target_id": "LDD_2024_D137",
          "anchor_text": "Điều 137",
          "description_summary": "..."
        }
      ],
      "tags": ["đất đai", "quyền sử dụng đất"]
    }
  ]
}
```

---

## Công nghệ

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| **Frontend** | Next.js 15, React 19, TypeScript 5.9 | App Router |
| **Styling** | TailwindCSS 4.1, tw-animate-css | Responsive |
| **UI** | lucide-react, react-markdown, motion | Icon + Markdown + animation |
| **Backend** | FastAPI, Uvicorn, Python | API bất đồng bộ |
| **Database** | PostgreSQL, Qdrant | Lưu trữ lâu dài |
| **LLM Framework** | LangChain (core, community, huggingface) | Điều phối LLM |
| **Embedding** | Fine-tuned BGE-M3 local artifact | Đa ngôn ngữ, 1024 chiều |
| **Vector DB** | Qdrant (Native Hybrid Search) | Cấu hình Named Vectors |
| **LLM Models** | Gemini Flash-Lite, HuggingFace Router models, Ollama local models | Provider cấu hình từ trình duyệt |

## Cấu hình suy luận khi triển khai

Khi triển khai, người dùng cấu hình LLM provider từ màn hình cấu hình trong trình duyệt.
API key do người dùng nhập chỉ được lưu trong profile trình duyệt hiện tại, sau đó được gửi
đến backend theo từng request chat. Backend chỉ dùng các key này trong bộ nhớ cho request
tương ứng và không lưu chúng.

Các vai trò suy luận:

- `answer`: sinh câu trả lời pháp lý cuối cùng.
- `rewriter`: vai trò rewrite query tùy chọn; cấu hình quality đã chấp nhận giữ `PIPELINE_REWRITER=none`.
- `summarizer`: cập nhật tóm tắt bộ nhớ hội thoại ở tác vụ nền.

Cấu hình khuyến nghị ban đầu:

```text
Provider: Google AI Studio
Answer model: Gemini 3.1 Flash-Lite
Rewriter model: Gemini 3.1 Flash-Lite
Summarizer model: Gemini 3.1 Flash-Lite
```

Embedding không được cấu hình bởi người dùng ở runtime. Retrieval stack dùng
fine-tuned local embedding model do server quản lý, để query dùng cùng không gian
embedding với corpus pháp luật đã index. Trong `remote_first`, thứ tự LLM provider
ưu tiên provider từ xa, nhưng query embedding vẫn đến từ artifact fine-tuned cục bộ.
Lỗi embedding được trả rõ cho client và không fallback sang Ollama, Hugging Face API
hoặc kết quả FAISS cũ.

Reranking an toàn khi triển khai:

- `PIPELINE_RERANKING=cross_encoder`: reranking bằng fine-tuned Cross-Encoder cục bộ
  từ `RERANKER_MODEL`. Mỗi request chấm điểm tối đa `RERANKER_MAX_CANDIDATES`
  tài liệu đã retrieval.
- `PIPELINE_RERANKING=none`: tắt reranking để khôi phục cấu hình hoặc kiểm tra vấn đề
  độ trễ.

Vai trò của các file môi trường:

- `.env`: cấu hình mặc định cho local/server, storage URL, tham số pipeline và API key fallback tùy chọn ở server.
- `.env.example`: template công khai với các key được hỗ trợ và giá trị mặc định an toàn.
- Bộ nhớ trình duyệt (browser storage): lưu BYOK API key của từng người dùng và provider/model đã chọn cho từng vai trò.

Khôi phục cấu hình: bỏ qua payload `inferenceConfig` từ trình duyệt và dùng cấu hình
mặc định phía server như `HUGGINGFACE_API_KEY`, `GOOGLE_API_KEY`,
`ENABLE_GOOGLE_FALLBACK` và `INFERENCE_STRATEGY`.

---

## Kiểm thử

Backend:

```bash
cd backend
.venv/bin/python -m pytest tests -q
.venv/bin/python -m compileall app scripts tests -q
.venv/bin/python -m pip check
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm run verify:models
npm run verify:inference-settings
```

Nếu Ruff đã được cài trong virtual environment của backend, có thể chạy thêm lệnh sau:

```bash
cd backend
.venv/bin/python -m ruff check app scripts tests
```

---

## Hạn chế đã biết

- Các bộ fixture đánh giá hiện còn nhỏ và không đại diện cho độ chính xác pháp lý tổng quát của toàn hệ thống.
- Corpus đã index chưa bao phủ toàn bộ văn bản pháp luật Việt Nam hoặc các thay đổi pháp luật trong tương lai.
- Câu trả lời phụ thuộc vào nội dung đã được index và vẫn có thể bỏ sót điều kiện, ngoại lệ hoặc chi tiết thủ tục thực tế.
- Bộ phát hiện tham chiếu không được hỗ trợ chỉ phục vụ mục đích diagnostic; số finding không đồng nghĩa với số lần hallucination.
- Các token SSE có thể được gửi trước bước kiểm tra citation cuối cùng; câu trả lời tổng hợp, sự kiện hoàn tất, dữ liệu đã lưu và lịch sử hội thoại đều dùng bản đã được làm sạch.
- Quá trình embedding và reranking chạy cục bộ trên CPU chậm hơn so với GPU.
- Đây là hệ thống nghiên cứu/đồ án sinh viên và không thay thế tư vấn pháp lý chuyên nghiệp.
## Chat history storage modes

Chat history storage is configured separately from `STORAGE_BACKEND`.

For deployments without authentication:

```env
CHAT_STORAGE_MODE=browser
NEXT_PUBLIC_CHAT_STORAGE_MODE=browser
STORAGE_BACKEND=qdrant_postgres
```

Browser mode keeps sessions, messages, summaries, and feedback in the current
browser instead of shared PostgreSQL tables. PostgreSQL chat mode is intended
only for trusted deployments because its history is shared without auth.
