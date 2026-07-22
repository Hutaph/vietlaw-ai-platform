# Hướng dẫn đóng góp

Tài liệu này mô tả quy ước làm việc cho VietLaw AI Platform. Mục tiêu là giữ
lịch sử thay đổi rõ ràng, review dễ hơn và hạn chế các thay đổi lan rộng ngoài
phạm vi cần thiết.

## Commit message

Commit message dùng chuẩn Conventional Commits và viết bằng tiếng Anh:

- `feat(scope): short summary`
- `fix(scope): short summary`
- `docs(scope): short summary`
- `refactor(scope): short summary`
- `chore(scope): short summary`

Ví dụ:

- `feat(storage): add database-backed storage bootstrap`
- `fix(api): handle storage initialization fallback`
- `docs(readme): translate deployment guide to vietnamese`

## Pull request

Pull request nên có cấu trúc ngắn gọn, dễ review.

### Tiêu đề

```text
feat(scope): short summary
```

### Mô tả

- Đã thay đổi gì
- Vì sao cần thay đổi
- Đã kiểm tra bằng cách nào
- Có việc nào cần theo dõi tiếp không

### Checklist

- [ ] Code build được hoặc các kiểm tra liên quan đã chạy
- [ ] Tài liệu đã được cập nhật nếu hành vi/cấu hình thay đổi
- [ ] Thay đổi được giới hạn trong phạm vi cần thiết
- [ ] Không commit secret, file `.env`, model artifact hoặc dữ liệu lớn ngoài ý muốn

## Quy ước tài liệu

- README và tài liệu hướng tới người dùng có thể viết bằng tiếng Việt.
- Commit message, branch name và PR title nên viết bằng tiếng Anh để dễ tra cứu.
- Tài liệu kỹ thuật nội bộ có thể dùng tiếng Việt hoặc tiếng Anh, nhưng cần nhất
  quán trong cùng một file.
- Comment trong code chỉ nên thêm khi giúp giải thích logic không hiển nhiên.

## Quy tắc làm việc

- Giữ thay đổi nhỏ, tập trung và dễ review.
- Ưu tiên tạo branch riêng như `feature/...`, `fix/...` hoặc `docs/...` trước
  khi sửa code.
- Không làm việc trực tiếp trên `main` khi triển khai tính năng lớn.
- Không revert thay đổi của người khác nếu chưa xác nhận.
- Luôn cập nhật tài liệu khi thay đổi setup, deploy hoặc hành vi người dùng nhìn
  thấy.
