## Why

Hiện tại, khi người dùng mở ứng dụng web, hệ thống tự động tải cuộc hội thoại gần nhất và gọi API để lấy toàn bộ tin nhắn cũ. Điều này gây lãng phí tài nguyên (thừa 1 API call) và làm chậm trải nghiệm nếu người dùng chỉ muốn bắt đầu một cuộc trò chuyện mới ngay lập tức (giống trải nghiệm của ChatGPT hay Claude).

## What Changes

- Sửa đổi logic khởi tạo trong `useChatSessions` hook (frontend) để mặc định tạo một session mới thay vì fetch tin nhắn của session gần nhất.
- Lịch sử các cuộc hội thoại cũ vẫn sẽ được hiển thị đầy đủ trên sidebar.
- Việc tải tin nhắn cho các session cũ sẽ chỉ xảy ra khi người dùng chủ động click vào sidebar (giữ nguyên tính năng lazy loading).

## Capabilities

### New Capabilities
*(None)*

### Modified Capabilities
- `lazy-chat-loading`: Sửa đổi yêu cầu "Session Metadata Startup" để KHÔNG fetch tin nhắn của session gần nhất, mà luôn khởi tạo một session mới.

## Impact

- **Frontend**: Thay đổi luồng tải dữ liệu mặc định trong `frontend/hooks/use-chat-sessions.ts`.
- **UX**: Tăng tốc độ hiển thị giao diện sẵn sàng chat, giảm độ trễ do gọi API không cần thiết.
- **Backend**: Giảm tải do không phải xử lý một request GET messages mỗi khi có người mở web.
