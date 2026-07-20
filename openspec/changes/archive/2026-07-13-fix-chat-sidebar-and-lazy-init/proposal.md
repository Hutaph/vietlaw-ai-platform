## Why

Có một lỗi xảy ra khi người dùng click vào một lịch sử hội thoại trong sidebar, tất cả các lịch sử hội thoại khác đều biến mất. Nguyên nhân là do cơ chế lọc session rỗng hoạt động sai với các session chưa được tải (lazy-load). Ngoài ra, người dùng không muốn hiển thị ngay mục "Cuộc trò chuyện mới" ở sidebar khi vừa vào web; giao diện ban đầu chỉ cần là một khung chat trống, và session mới chỉ nên xuất hiện sau khi người dùng thực sự chat.

## What Changes

- Sửa lỗi lọc mất session trong hàm `handleSelectSession`.
- Sửa đổi hàm `loadFromDB` và `handleNewChat`: Không chèn "Cuộc trò chuyện mới" vào state `sessions` ngay từ đầu.
- Cập nhật hàm `addMessage`: Khi có tin nhắn đầu tiên, mới khởi tạo object `ChatSession` và đưa lên đầu danh sách `sessions`.

## Capabilities

### New Capabilities
*(None)*

### Modified Capabilities
- `lazy-chat-loading`: Sửa đổi yêu cầu về `Session Metadata Startup` để làm rõ việc KHÔNG sinh ra session ảo trên giao diện, mà chỉ bắt đầu lưu session khi có tin nhắn thật.

## Impact

- **Frontend**: Thay đổi lớn trong cách quản lý state của `useChatSessions` hook.
- **UX**: Sidebar gọn gàng hơn, khắc phục hoàn toàn lỗi mất lịch sử, chuẩn hóa trải nghiệm giống ChatGPT/Claude.
