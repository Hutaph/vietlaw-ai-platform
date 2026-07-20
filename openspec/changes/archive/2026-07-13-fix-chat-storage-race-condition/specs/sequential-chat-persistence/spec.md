## ADDED Requirements

### Requirement: Sequential turn persistence
Hệ thống SHALL đảm bảo rằng trong mỗi lượt hội thoại, tin nhắn của user và tin nhắn của assistant PHẢI được lưu vào PostgreSQL theo thứ tự tuần tự: `ensure_session_exists` → `save_chat_message(user)` → `save_chat_message(assistant)`. Không được phép phát ra 3 task song song độc lập.

#### Scenario: Successful turn persist on stream endpoint
- **WHEN** streaming hoàn tất và accumulated_text không rỗng
- **THEN** `chat_sessions` chứa row với `session_id` tương ứng
- **AND** `chat_messages` chứa đúng 2 rows: role=user và role=assistant, theo thứ tự created_at
- **AND** cả 2 rows đều có `content` không rỗng

#### Scenario: Successful turn persist on non-stream endpoint
- **WHEN** `/chat` trả về response thành công
- **THEN** `chat_messages` chứa đúng cặp (user, assistant) cho lượt đó
- **AND** câu hỏi của user có nội dung trùng với `last_message` trong request

#### Scenario: Successful turn persist on cache hit path
- **WHEN** semantic cache trả về cached response trong streaming endpoint
- **THEN** cặp (user, assistant) vẫn được lưu đầy đủ vào `chat_messages`

#### Scenario: FK constraint never violated
- **WHEN** `save_chat_message` được gọi
- **THEN** `chat_sessions` luôn đã tồn tại row tương ứng trước đó
- **AND** không có lỗi FK violation nào được ghi vào log
