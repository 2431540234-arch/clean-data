# Ma trận quyền Admin / User

> TODO: hoàn thiện bảng dưới đây cho từng nhóm API.

| Hành động | Admin | User (owner) | User (không phải owner) |
|---|---|---|---|
| Xem/tạo/sửa/xóa project của chính mình | ✅ | ✅ | ❌ |
| Xem/sửa/xóa project của người khác | ✅ | ❌ | ❌ |
| Upload dataset vào project | ✅ (mọi project) | ✅ (project của mình) | ❌ |
| Áp dụng rule / undo / redo | ✅ | ✅ (dataset của mình) | ❌ |
| Xem audit log của chính mình | ✅ | ✅ | ✅ |
| Xem audit log toàn hệ thống | ✅ | ❌ | ❌ |
| Quản lý user (khóa/mở, đổi quyền) | ✅ | ❌ | ❌ |
| Xem thống kê hệ thống | ✅ | ❌ | ❌ |

## Cơ chế thực thi

- `app.core.deps.require_admin`: chặn ở tầng dependency cho các route chỉ-admin.
- `app.core.permissions.ensure_can_access_project`: kiểm tra `owner_id` so với user hiện
  tại cho các route liên quan tới project/dataset.
- TODO: bổ sung chi tiết cách áp dụng cho dataset_versions, suggestions, rules (đều đi
  qua project cha để xác định quyền).
