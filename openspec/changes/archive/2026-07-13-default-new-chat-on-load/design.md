## Context

Hiện tại, khi ứng dụng load (trong `useChatSessions`), luồng khởi tạo sẽ fetch `/api/chat/sessions`, chọn session mới nhất (phần tử đầu tiên) và gọi tiếp `/api/chat/session/[id]/messages` để tải dữ liệu lịch sử. Điều này làm tăng độ trễ trước khi người dùng có thể thực sự tương tác, và trái với kỳ vọng phổ biến (như ChatGPT) là bắt đầu ở giao diện chat mới.

## Goals / Non-Goals

**Goals:**
- Tối ưu hóa thời gian tải ban đầu bằng cách bỏ lệnh fetch messages.
- Mở mặc định một giao diện "Cuộc trò chuyện mới" trống và sẵn sàng nhập nội dung.
- Không ảnh hưởng đến dữ liệu session cũ trong sidebar (vẫn hiển thị).

**Non-Goals:**
- Không sửa đổi backend API.
- Không làm thay đổi luồng xử lý của tính năng `handleNewChat` hoặc `handleSelectSession` đã có.

## Decisions

### D1: Tạo "Cuộc trò chuyện mới" thủ công ở Frontend khi khởi tạo
Thay vì gọi `handleNewChat()` (hàm này phụ thuộc vào `stateRef.current` có thể chưa đồng bộ lúc mới load `dbSessions`), ta sẽ khởi tạo một object `ChatSession` rỗng (id mới, title: "Cuộc trò chuyện mới") và ghim nó vào đầu danh sách `loadedSessions` ngay trong hàm `loadFromDB()`.

**Rationale**: Việc này đảm bảo React state `sessions` được cập nhật đồng nhất trong 1 lần `setSessions(loadedSessions)` thay vì 2 lần (fetch xong -> set -> gọi handleNewChat -> set tiếp). Điều này giúp UI không bị chớp (flicker) và loại bỏ hoàn toàn lời gọi API fetch messages.

## Risks / Trade-offs

- **[Risk]** Người dùng muốn tiếp tục ngay cuộc trò chuyện cũ bị thêm 1 thao tác click (vào sidebar).
  - **Mitigation**: Đổi lại UX sạch sẽ và nhanh hơn (chấp nhận trade-off vì là chuẩn chung của các web chat AI hiện đại).
- **[Risk]** Lỗi logic `currentSessionId` không map đúng với danh sách.
  - **Mitigation**: Cần gán `setCurrentSessionId(newId)` đồng thời khi thêm new session vào danh sách `loadedSessions`.
