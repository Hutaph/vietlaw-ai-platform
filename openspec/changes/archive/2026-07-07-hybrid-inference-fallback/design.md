## Context

Hiện tại, hệ thống RAG đang gọi trực tiếp các mô hình thông qua Interface (ví dụ: `BaseEmbedding`, `ChatOpenAI`). Tuy nhiên, việc khởi tạo mô hình lại phụ thuộc vào các cờ cố định như `HUGGINGFACE_EMBEDDING_MODE=local` hoặc hardcode URL. Hệ thống thiếu một cơ chế bao bọc để thử nghiệm mô hình chính (Primary), và tự động gọi mô hình phụ (Secondary) nếu mô hình chính bị lỗi (như Timeout, ModelNotFound, RateLimitError).

## Goals / Non-Goals

**Goals:**
- Tạo ra một wrapper logic cho phép bao bọc việc thực thi (inference) của bất kỳ lớp nào (Embedding, Reranker, LLM).
- Xác định rõ 2 luồng: `Primary` (Ví dụ: HuggingFace/Remote) và `Fallback` (Ví dụ: Ollama/Local).
- Tự động bắt lỗi (Exception) và retry qua luồng Fallback, nếu cả 2 đều hỏng, ném lỗi rõ ràng cho Frontend.

**Non-Goals:**
- Tích hợp thêm các model APIs mới (như AWS Bedrock, Azure) - chỉ sử dụng các provider hiện có.
- Thay đổi cấu trúc Prompt hoặc chiến lược Chunking.

## Decisions

**1. Inference Fallback Wrapper (Decorator or Class Proxy)**
- **Lựa chọn:** Xây dựng một Class tên là `InferenceFallbackManager` có chức năng nhận vào 2 đối tượng `primary_service` và `fallback_service`. Khi gọi hàm `.invoke()` hoặc `.embed()`, nó sẽ gọi `primary_service` trong vòng block `try-except`. Nếu lỗi, nó ghi log cảnh báo và gọi `fallback_service`.
- **Lý do:** Giúp việc refactor code dễ dàng, chỉ cần đổi cách khởi tạo các service trong `backend/app/services/pipeline.py` mà không phải thay đổi nội hàm của từng class Embedding/Reranking hiện hữu.

**2. Quản lý LLM**
- Sử dụng `langchain_core.runnables.Fallback` (tính năng `with_fallbacks` của Langchain). Cụ thể: `llm = primary_llm.with_fallbacks([fallback_llm])`.
- **Lý do:** Langchain hỗ trợ cực tốt cơ chế tự động fallback cho ChatModel. Không cần tự code vòng lặp.

**3. Cấu hình biến môi trường (`.env`)**
- Bổ sung `INFERENCE_STRATEGY=remote_first` (thử remote trước, lỗi thì local) hoặc `local_first` (thử local trước, lỗi thì remote).

## Risks / Trade-offs

- **Risk 1:** Delay quá lâu nếu Remote API bị treo (hang) thay vì trả về lỗi ngay.
  - *Mitigation:* Đặt `timeout=10` cho Primary model để ép ném exception nếu phản hồi quá lâu.
- **Risk 2:** Fallback model (thường yếu hơn) có thể trả về câu trả lời sai format (ví dụ quên trả về XML `<cite>`).
  - *Mitigation:* Đưa một log cảnh báo (Warning) trong backend để Admin biết quá trình Fallback đã diễn ra, dễ theo dõi chất lượng.
