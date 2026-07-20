## 1. Cập nhật Sidebar Rendering (Không hiển thị "New Chat" ảo)

- [x] 1.1 Sửa hàm `loadFromDB`: Xóa đoạn mã `loadedSessions.unshift(newSession);`. Giữ nguyên việc set `currentSessionId(newId)`.
- [x] 1.2 Sửa hàm `handleNewChat`: Khi người dùng tạo chat mới thủ công, set `currentSessionId(newId)` và `messagesBySession` rỗng, nhưng KHÔNG gọi `setSessions([newSession, ...validSessions])`.

## 2. Cập nhật Behavior Thêm Tin Nhắn (Lưu Session)

- [x] 2.1 Sửa hàm `addMessage`: Khi thêm một tin nhắn, kiểm tra xem `currentSessionId` đã có trong mảng `sessions` hay chưa. Nếu chưa có, tạo object `ChatSession` mới (lấy một phần nội dung tin nhắn làm title) và `unshift` nó vào `setSessions(prev)`.

## 3. Khắc phục Bug Lọc Session

- [x] 3.1 Sửa hàm `handleSelectSession`: Loại bỏ điều kiện `.filter(...)` rườm rà. Chỉ đơn giản set `currentSessionId(id)` và lazy load messages (không đụng chạm tới mảng `sessions`).

## 4. Kiểm thử

- [x] 4.1 Vào web lần đầu: Khung chat trống, sidebar không hiện "Cuộc trò chuyện mới".
- [x] 4.2 Bắt đầu gõ chat: Ngay khi tin nhắn gửi đi, sidebar tự động cập nhật hiển thị lịch sử này ở trên cùng với tiêu đề tự trích xuất từ câu hỏi.
- [x] 4.3 Click sang lịch sử khác: Chuyển bình thường, lịch sử cũ không bị biến mất khỏi sidebar.
