# Ma trận quyền Admin / User

Hai quyền: `admin` và `user` (người dùng thường). Mọi API (trừ đăng ký, đăng nhập, `/health`) cần JWT.
Quyền được kiểm tra ở **backend**; giao diện chỉ ẩn bớt trang cho gọn, không phải lớp bảo vệ.

| Hành động | Admin | User (owner) | User (không phải owner) |
|---|---|---|---|
| Xem/tạo/sửa/xóa project của chính mình | ✅ | ✅ | ❌ (403) |
| Xem/sửa/xóa project của người khác | ✅ | ❌ | ❌ (403) |
| Xem danh sách project | ✅ (tất cả) | ✅ (của mình) | — |
| Upload dataset, chọn sheet Excel | ✅ (mọi project) | ✅ (project của mình) | ❌ (403) |
| Xem dataset, phiên bản, dòng dữ liệu, danh sách dataset của project | ✅ | ✅ | ❌ (403) |
| Profiling, xem lỗi đã phát hiện, điểm chất lượng | ✅ | ✅ (dataset của mình) | ❌ (403) |
| Mapping cột, sinh/duyệt gợi ý làm sạch | ✅ | ✅ (dataset của mình) | ❌ (403) |
| Xem trước, áp dụng rule, undo / redo / khôi phục phiên bản | ✅ | ✅ (dataset của mình) | ❌ (403) |
| Xuất CSV / Excel | ✅ | ✅ (dataset của mình) | ❌ (403) |
| Lưu / xem / xóa rule mẫu của project | ✅ | ✅ (project của mình) | ❌ (403) |
| Xóa rule hệ thống (không thuộc project nào) | ✅ | ❌ | ❌ |
| Đổi mật khẩu của chính mình | ✅ | ✅ | ✅ |
| Xem audit log của chính mình (`/audit/me`) | ✅ | ✅ | ✅ |
| Xem audit log toàn hệ thống (`/audit/all`) | ✅ | ❌ (403) | ❌ (403) |
| Quản lý user: danh sách, khóa/mở khóa, đổi quyền, đặt lại mật khẩu | ✅ | ❌ (403) | ❌ (403) |
| Xem thống kê hệ thống | ✅ | ❌ (403) | ❌ (403) |

Quy ước mã lỗi: chưa đăng nhập hoặc token hết hạn → **401**; tài nguyên không tồn tại → **404**;
có tồn tại nhưng không thuộc về bạn → **403** (xem "Cải thiện sau" trong tổng kết: có thể đổi sang 404 để
không lộ việc tài nguyên tồn tại).

## Cơ chế thực thi

- `app.core.deps.require_admin`: chặn ở tầng dependency cho toàn bộ router `/admin` và `/audit/all`.
- `app.services.access` là **điểm duy nhất** lấy dữ liệu có kiểm tra quyền:
  `get_owned_project`, `get_owned_dataset`, `get_owned_version`, `get_owned_suggestion`. Quyền của
  dataset, phiên bản và gợi ý đều suy ra từ **project cha** qua `app.core.permissions.ensure_can_access_project`
  (so `owner_id` với user hiện tại; admin luôn qua). Mọi router đi qua các hàm này nên không có endpoint
  "quên" kiểm tra quyền.
- Bài kiểm tra `tests/integration/test_data_isolation.py` gọi 27 endpoint bằng một user khác và xác nhận
  tất cả trả 403 mà không rò rỉ nội dung, chưa đăng nhập trả 401, admin đọc được.

## Bảo vệ tài khoản

- **Khóa tài khoản:** token của tài khoản bị khóa bị từ chối ngay (`get_current_user` kiểm tra `is_active`).
- **Quyền lấy từ DB, không từ token:** đổi role có hiệu lực ngay, kể cả với token đã cấp.
- **Không để mất admin:** không hạ quyền hoặc khóa quản trị viên đang hoạt động cuối cùng (409).
- **Thu hồi token:** sau khi đổi hoặc đặt lại mật khẩu (`users.password_changed_at`), mọi token cấp trước
  thời điểm đó bị từ chối. Đổi mật khẩu trả kèm token mới cho phiên hiện tại.
- **Chặn dò mật khẩu:** sai quá 5 lần trong 15 phút theo cặp (email, IP) → 429; thêm trần theo IP.
- **Nhật ký:** `auth.login`, `auth.login_failed` (không bao giờ ghi mật khẩu), `auth.register`,
  `auth.change_password`, `user.lock|unlock|change_role|reset_password`.
