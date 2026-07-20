## Context

Hệ thống Vietnam Legal QA sử dụng PostgreSQL để lưu trữ lịch sử chat (sessions và messages). Khi endpoint `/chat/stream` (và `/chat`) hoàn tất quá trình sinh text, backend phát ba `asyncio.create_task(asyncio.to_thread(...))` song song để:

1. `ensure_session_exists(session_id, title)` — tạo row trong `chat_sessions` nếu chưa tồn tại.
2. `save_chat_message(... "user" ...)` — lưu câu hỏi vào `chat_messages`.
3. `save_chat_message(... "assistant" ...)` — lưu phản hồi AI vào `chat_messages`.

Vì `chat_messages` có foreign key tham chiếu đến `chat_sessions`, Thread 2 thường thất bại với lỗi FK violation khi Thread 1 chưa commit xong. Hậu quả: câu hỏi của user bị mất, AI response được lưu thành công, dẫn đến lịch sử hiển thị sai và thống kê admin không đầy đủ.

## Goals / Non-Goals

**Goals:**
- Đảm bảo cặp (user_message, assistant_message) luôn được ghi đầy đủ vào PostgreSQL trong mỗi lượt hội thoại.
- Không tăng độ trễ cảm nhận của người dùng (vẫn chạy persist ngầm sau khi stream xong).
- Cập nhật `list_sessions()` để trả thêm `message_count` giúp sidebar phản ánh đúng trạng thái.

**Non-Goals:**
- Không thay đổi schema DB (không thêm/xóa cột hay bảng).
- Không thêm retry logic phức tạp hay dead-letter queue.
- Không thay đổi giao thức SSE hay cấu trúc API response.

## Decisions

### D1: Gộp 3 create_task thành 1 coroutine tuần tự

**Quyết định**: Tạo hàm async helper `_persist_turn()` nhận đầy đủ tham số, chạy `ensure_session_exists → save_chat_message(user) → save_chat_message(assistant)` lần lượt với `await asyncio.to_thread(...)`, rồi dispatch toàn bộ như một `asyncio.create_task(_persist_turn(...))`.

**Lý do**: Thay vì sửa từng điểm riêng lẻ, việc đóng gói vào một hàm:
- Loại bỏ race condition tại gốc (sequential ordering đảm bảo FK constraint luôn thỏa mãn).
- Vẫn non-blocking với người dùng (task chạy sau khi yield/response).
- DRY: 3 code path (non-streaming, streaming, streaming+cache hit) dùng chung 1 hàm.

**Alternatives considered**:
- *Dùng transaction*: Không giải quyết được vấn đề vì các thread vẫn có thể bắt đầu transaction trước khi session tồn tại.
- *Chạy đồng bộ trước khi return response*: Sẽ tăng độ trễ cảm nhận, không cần thiết.

### D2: Thêm `message_count` vào `list_sessions()`

**Quyết định**: Cập nhật query SQL trong `storage.list_sessions()` để JOIN với `chat_messages` và đếm số lượng message per session.

**Lý do**: Frontend hiện tại không thể biết session nào có tin nhắn mà không fetch từng session. Thêm `message_count` cho phép sidebar lọc ra các session "phantom" (chưa có tin nhắn) mà không cần extra requests.

**Alternatives considered**:
- *Thêm endpoint mới*: Không cần thiết, đây là thông tin tự nhiên thuộc danh sách session.

### D3: Cập nhật `useChatSessions.ts` để consume `message_count`

**Quyết định**: Khi load sessions từ DB, chỉ đưa vào danh sách render những session có `message_count > 0` (hoặc là session hiện tại đang active).

**Lý do**: Loại bỏ "session rỗng" khỏi sidebar khi user refresh, tránh nhầm lẫn.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `_persist_turn()` throw exception → cả cặp message bị mất | Bọc toàn bộ trong try/except, log lỗi với đầy đủ context (session_id, role) |
| `message_count` JOIN làm chậm `list_sessions()` khi có nhiều session | COUNT + GROUP BY có index tốt trên `session_id`; nếu cần thêm vào tương lai có thể cache |
| Session rỗng (mới tạo, chưa có tin nhắn) bị lọc ra khỏi sidebar | Luôn giữ `currentSessionId` trong danh sách dù `message_count = 0` |
