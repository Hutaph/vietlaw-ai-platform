# 🎯 Fine-Tuning Legal Retrieval Models

Thư mục này chứa toàn bộ pipeline (data generation, notebooks, scripts) phục vụ cho việc huấn luyện tinh chỉnh (fine-tuning) các mô hình Retrieval cho ngôn ngữ pháp lý Việt Nam.

## 📂 Cấu trúc thư mục

```
fine-tuning/
│
├── data/                       # Chứa dữ liệu huấn luyện
│   ├── synthetic/              # Dữ liệu QA pairs được sinh từ LLM
│   └── training/               # Dữ liệu đã format chuẩn (JSONL, CSV) cho training
│
├── embedding/                  # Tinh chỉnh Bi-Encoder (Embedding Model - BAAI/bge-m3)
│   ├── notebooks/
│   │   ├── 01_data_generation.ipynb       # Dùng LLM (Gemma/Qwen) sinh câu hỏi từ Điều luật
│   │   ├── 02_finetune_bge_m3.ipynb       # Script fine-tune Sentence-Transformers (MNRL loss)
│   │   └── 03_evaluation.ipynb            # Đánh giá so sánh model gốc vs model đã finetune
│   └── scripts/                           # Các script chạy training trên server
│
├── reranking/                  # Tinh chỉnh Cross-Encoder (Reranker)
│   ├── notebooks/
│   │   ├── 01_data_preparation.ipynb      # Lấy top-k từ FAISS tạo cặp (query, doc) hard-negatives
│   │   ├── 02_finetune_cross_encoder.ipynb # Fine-tune mô hình classification
│   │   └── 03_evaluation.ipynb            # Đánh giá điểm NDCG, MRR
│   └── scripts/                           # Các script chạy training trên server
│
└── README.md                   # Hướng dẫn quy trình fine-tuning
```

## 🚀 Quy trình cơ bản

### 1. Fine-tune Embedding (Bi-Encoder)
- **Mục tiêu**: Kéo vector của Câu hỏi (Query) và Điều luật tương ứng (Positive Document) lại gần nhau. Đẩy các điều luật không liên quan (Negative) ra xa.
- **Phương pháp**: Sử dụng Multiple Negatives Ranking Loss (MNRL). Cần tạo dataset có dạng `(query, positive_doc)`.

### 2. Fine-tune Reranker (Cross-Encoder)
- **Mục tiêu**: Mô hình nhận vào cùng lúc `[Query, Document]` và dự đoán điểm Relevance (0 -> 1).
- **Phương pháp**: Phân loại nhị phân (Binary Classification Loss). Cần dataset có dạng `(query, doc, label)` bao gồm cả Hard Negatives lấy từ vector search.
