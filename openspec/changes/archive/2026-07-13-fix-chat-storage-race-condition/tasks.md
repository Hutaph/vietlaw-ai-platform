## 1. Backend — Tạo hàm `_persist_turn()` dùng chung

- [x] 1.1 Trong `backend/app/api/chat.py`, thêm hàm async `_persist_turn(session_id, session_title, user_msg_id, user_content, ai_msg_id, ai_content, ai_context)` chạy tuần tự: `ensure_session_exists` → `save_chat_message(user)` → `save_chat_message(assistant)` bằng `await asyncio.to_thread(...)`. Bọc toàn bộ trong try/except và log lỗi rõ ràng.
- [x] 1.2 Xoá 3 `asyncio.create_task` riêng lẻ trong code path của endpoint **`POST /chat`** (non-streaming) và thay bằng một `asyncio.create_task(_persist_turn(...))` duy nhất.
- [x] 1.3 Xoá 3 `asyncio.create_task` riêng lẻ trong code path **streaming thông thường** (`accumulated_text` path) trong `event_generator()` và thay bằng `asyncio.create_task(_persist_turn(...))`.
- [x] 1.4 Xoá 3 `asyncio.create_task` riêng lẻ trong code path **cache hit** trong `event_generator()` và thay bằng `asyncio.create_task(_persist_turn(...))`.

## 2. Backend — Cập nhật `list_sessions()` để trả `message_count`

- [x] 2.1 Trong `backend/app/services/storage.py`, cập nhật hàm `list_sessions()`: thay query hiện tại bằng query có LEFT JOIN với `chat_messages` và `COUNT(cm.id) AS message_count`, GROUP BY `session_id`, để mỗi session object trong kết quả có trường `message_count`.
- [x] 2.2 Cập nhật kiểu trả về trong docstring và mapping dict trong `list_sessions()` để bao gồm key `message_count`.

## 3. Frontend — Consume `message_count` trong `useChatSessions`

- [x] 3.1 Trong `frontend/hooks/use-chat-sessions.ts`, cập nhật hàm `loadFromDB()`: khi map `dbSessions` thành `loadedSessions`, đọc thêm trường `message_count` và lưu vào `ChatSession` (hoặc dùng trực tiếp trong bước lọc).
- [x] 3.2 Trong `loadFromDB()`, lọc `loadedSessions` trước khi `setSessions`: chỉ giữ lại session có `message_count > 0`. Luôn giữ session đầu tiên (sẽ là `currentSessionId`) dù `message_count` bằng 0 để tránh UI trống.
- [x] 3.3 Kiểm tra lại logic `handleNewChat()`: session mới tạo (chưa có `message_count`) vẫn phải hiển thị trong sidebar khi đang active. Đảm bảo `currentSessionId` luôn có mặt trong danh sách `sessions`.

## 4. Kiểm thử và xác minh

- [x] 4.1 Khởi động backend và frontend, gửi một tin nhắn mới, sau đó **refresh** trang. Xác nhận cả câu hỏi (user) lẫn phản hồi (AI) đều hiển thị đúng trong history.
- [x] 4.2 Truy cập trang Admin/thống kê, xác nhận lượt hội thoại vừa thực hiện được ghi nhận đúng (total_interactions tăng, by_date cập nhật).
- [x] 4.3 Kiểm tra backend log: xác nhận không còn dòng `FK violation` hay `Error saving chat message` sau khi fix.
- [x] 4.4 Tạo một session mới, chưa nhắn tin, sau đó refresh — xác nhận session rỗng không xuất hiện trong sidebar (đã bị lọc bởi `message_count = 0`).
