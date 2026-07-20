## 1. Cập nhật Hook `useChatSessions` (Frontend)

- [x] 1.1 Xóa block code fetch messages cho session đầu tiên (`loadedSessions[0]`) trong hàm `loadFromDB`.
- [x] 1.2 Trong hàm `loadFromDB`, khởi tạo thủ công một `newSession` rỗng (có ID sinh bằng Date.now(), title: "Cuộc trò chuyện mới").
- [x] 1.3 Thêm `newSession` này vào đầu mảng `loadedSessions` và cập nhật state thông qua `setSessions(loadedSessions)`.
- [x] 1.4 Thiết lập `setCurrentSessionId` thành ID của session mới này và khởi tạo `messagesBySession` bằng rỗng cho ID đó.
- [x] 1.5 Bỏ các lệnh gọi `setIsSessionLoading` trong luồng load ban đầu vì không còn call API fetch messages.

## 2. Kiểm thử và xác minh

- [x] 2.1 Khởi động frontend, mở ứng dụng và xác nhận sidebar hiển thị "Cuộc trò chuyện mới" ở trên cùng (được chọn mặc định).
- [x] 2.2 Xác nhận vùng chat chính trống rỗng, sẵn sàng nhập tin nhắn.
- [x] 2.3 Kiểm tra tab Network, đảm bảo không có bất kỳ request API nào gọi tới `/api/chat/session/.../messages` khi trang vừa khởi động.
- [x] 2.4 Click vào một session cũ dưới sidebar, xác nhận messages được lazy-load về và hiển thị đầy đủ.
