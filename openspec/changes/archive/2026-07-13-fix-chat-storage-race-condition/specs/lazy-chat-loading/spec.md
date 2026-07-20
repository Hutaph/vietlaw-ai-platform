## MODIFIED Requirements

### Requirement: Session list includes message count
API `GET /chat/sessions` SHALL trả về danh sách sessions trong đó mỗi session object PHẢI bao gồm trường `message_count` kiểu integer biểu thị số lượng messages thuộc session đó. Trường này PHẢI được tính toán server-side thông qua SQL COUNT, không phải client-side.

#### Scenario: Sessions returned with message count
- **WHEN** client gọi `GET /chat/sessions`
- **THEN** mỗi object trong mảng kết quả có trường `message_count` kiểu số nguyên không âm

#### Scenario: Empty session has zero message count
- **WHEN** session tồn tại trong `chat_sessions` nhưng không có rows nào trong `chat_messages`
- **THEN** `message_count` = 0 cho session đó

#### Scenario: Frontend filters empty sessions from sidebar
- **WHEN** `useChatSessions` nhận danh sách sessions từ API
- **THEN** chỉ những session có `message_count > 0` HOẶC là `currentSessionId` hiện tại mới được hiển thị trong sidebar
