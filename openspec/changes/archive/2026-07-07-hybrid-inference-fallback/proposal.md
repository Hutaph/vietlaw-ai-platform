## Why

Hệ thống Agentic RAG hiện tại phụ thuộc cứng vào cấu hình đơn lẻ cho mỗi layer Inference (LLM, Embedding, Reranking). Điều này dẫn đến Single Point of Failure (SPOF) - nếu API Remote bị rate limit hoặc đứt mạng, toàn bộ hệ thống sẽ tê liệt. Ngược lại, nếu chạy Local bị quá tải RAM/VRAM, hệ thống cũng không thể tự xoay sở.
Cần thiết kế lại kiến trúc theo dạng Hybrid Inference Fallback: Hỗ trợ cấu hình hai chế độ (Local & Remote) cho toàn bộ pipeline, có khả năng tự động chuyển đổi sang phương án dự phòng khi phương án chính thất bại.

## What Changes

- Refactor lại toàn bộ các class trong `backend/app/services` (`llm.py`, `embedding/`, `reranking/`, `rewriting/`) để hỗ trợ cấu hình 2 chế độ.
- Thêm cơ chế Fallback Wrapper để tự động bắt Exception (Timeout, RateLimit, ConnectionError) và gọi sang model dự phòng.
- Thêm logic ném ngoại lệ (Exception) rõ ràng về API khi cả 2 chế độ đều sập.
- Cập nhật file `.env` để hỗ trợ linh hoạt lựa chọn cấu hình (ví dụ ưu tiên remote trước, local sau hoặc ngược lại).

## Capabilities

### New Capabilities
- `hybrid-inference-manager`: Core capability cho phép điều phối, quản lý lỗi và tự động fallback giữa các Inference Providers (Local/Remote).

### Modified Capabilities


## Impact

- **Affected Code**: 
  - `backend/app/services/llm.py`
  - `backend/app/services/embedding/*`
  - `backend/app/services/reranking/*`
  - `backend/app/services/rewriting/*`
  - `backend/app/services/pipeline.py`
- **Environment**: Bổ sung các cấu hình mode vào `.env`.
