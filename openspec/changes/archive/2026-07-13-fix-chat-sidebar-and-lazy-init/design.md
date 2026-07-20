## Context

Trong bản sửa trước, chúng ta đã thay đổi logic để tạo ra một session "Cuộc trò chuyện mới" trong `loadedSessions` ngay khi app load, nhằm tránh việc gọi API dư thừa. Tuy nhiên, logic lọc trong `handleSelectSession` đã vô tình xóa các lịch sử hội thoại khác chưa được tải (`messagesBySession[s.id] === undefined`). Hơn nữa, UX chuẩn của các ứng dụng AI hiện đại (ChatGPT, Claude) không hiển thị item "New Chat" ở sidebar cho đến khi người dùng gửi tin nhắn đầu tiên.

## Goals / Non-Goals

**Goals:**
- Khắc phục lỗi sidebar biến mất khi click chọn một session cũ.
- Áp dụng state model mới cho sidebar: Chỉ hiện các session thực sự có tin nhắn. 
- Vẫn duy trì giao diện chat trống ngay khi vào web (bằng cách quản lý `currentSessionId` riêng biệt).

**Non-Goals:**
- Không thay đổi thiết kế backend API.
- Không thay đổi giao diện (UI CSS).

## Decisions

### D1: Không add "Cuộc trò chuyện mới" vào mảng `sessions` từ đầu
Khi app load (`loadFromDB`) hoặc khi bấm nút "New Chat" (`handleNewChat`), chúng ta chỉ tạo ra một ID tạm gán cho `currentSessionId`, đồng thời khởi tạo mảng rỗng trong `messagesBySession[newId] = []`. Ta **KHÔNG** đưa object `ChatSession` giả vào mảng `sessions`.
*Lợi ích*: Sidebar sẽ chỉ render các session thực tế. UI gọn gàng.

### D2: Tự động đưa session vào sidebar khi có tin nhắn (`addMessage`)
Trong `addMessage`, ta kiểm tra xem `currentSessionId` đã có mặt trong mảng `sessions` chưa. Nếu chưa (tức là người dùng vừa gõ câu hỏi đầu tiên ở khung chat rỗng), ta tạo object `ChatSession` với tiêu đề lấy từ 40 ký tự đầu của tin nhắn, sau đó `unshift` lên đầu mảng `sessions`.
*Lợi ích*: Khắc phục được việc chat bị "vô danh", đồng bộ trạng thái ngay tức khắc mà không cần refresh.

### D3: Sửa lỗi `handleSelectSession` 
Bỏ hẳn đoạn code `prev.filter(...)` lỗi thời đi. Ta không cần thiết phải "dọn dẹp" các empty session nữa, vì theo D1, empty session thậm chí còn không nằm trong mảng `sessions` từ đầu. (Ngoại trừ trường hợp hiếm hoi bị lỗi db, nhưng nếu có thì cứ giữ nguyên cũng không sao, hoặc xử lý ở API trả về). 

## Risks / Trade-offs

- **[Risk]** Nếu API fetch list sessions từ backend trả về các session lỗi (không có message_count), filter cũ có thể sẽ khiến chúng hiển thị ở sidebar.
  - **Mitigation**: API backend hiện tại đã xử lý `message_count` và ta vẫn giữ lệnh filter `dbSessions.filter(s => s.message_count > 0)` khi mới lấy từ API.
