## Why

Khi người dùng gửi tin nhắn, backend phát ra 3 `asyncio.create_task` song song để (1) đảm bảo session tồn tại, (2) lưu câu hỏi của user, và (3) lưu phản hồi AI. Do chúng chạy không tuần tự, Thread lưu câu hỏi của user thường thất bại vì session chưa kịp được tạo (vi phạm khóa ngoại), dẫn đến mất câu hỏi sau khi refresh và không ghi nhận vào thống kê/lịch sử.

## What Changes

- Gộp 3 lệnh persist riêng rẽ thành một hàm helper `_persist_turn()` chạy tuần tự (await-chain): `ensure_session_exists` → `save_chat_message(user)` → `save_chat_message(assistant)`.
- Bọc hàm này trong một coroutine và dispatch nó dưới dạng một `asyncio.create_task` duy nhất để vẫn chạy ngầm, không block streaming.
- Áp dụng thay đổi cho 3 nơi trong `backend/app/api/chat.py`: endpoint `/chat` (non-streaming), endpoint `/chat/stream` (streaming thông thường), và endpoint `/chat/stream` (cache hit path).
- Cập nhật hook `useChatSessions.ts` ở frontend: khi load lại session từ DB, bổ sung trường `message_count` vào danh sách session để sidebar phản ánh đúng số lượng tin nhắn.

## Capabilities

### New Capabilities

- `sequential-chat-persistence`: Lưu trữ tuần tự đảm bảo cặp (user, assistant) luôn được ghi đầy đủ vào PostgreSQL trong mỗi lượt hội thoại.

### Modified Capabilities

- `lazy-chat-loading`: Bổ sung `message_count` vào API list sessions để frontend không cần fetch từng session riêng lẻ để biết session có tin nhắn hay không.

## Impact

- **Backend**: `backend/app/api/chat.py` — refactor phần persist trong cả 3 code path.
- **Backend**: `backend/app/services/storage.py` — cập nhật `list_sessions()` để trả thêm `message_count`.
- **Frontend**: `frontend/hooks/use-chat-sessions.ts` — consume `message_count` khi render danh sách session trong sidebar.
- **Không breaking**: Tất cả API contract hiện tại (shape của JSON response) vẫn được giữ nguyên; chỉ thêm trường mới.
