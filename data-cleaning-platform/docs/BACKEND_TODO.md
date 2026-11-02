# BACKEND_TODO: việc backend còn thiếu theo nhu cầu của frontend

Tài liệu này do phần frontend lập, dùng để làm backend tiếp theo. Nội dung gồm:

1. **Endpoint đã khai báo nhưng chưa cài đặt** (`raise NotImplementedError`, trả HTTP 500).
2. **Endpoint frontend cần nhưng backend chưa có** (frontend không tự bịa).
3. Quy ước frontend đang dựa vào, để backend giữ đúng.

Chạy frontend với dữ liệu mẫu để xem giao diện khi backend chưa xong: `FRONTEND_MOCK=1`
(xem `frontend/mock_api.py`, mock bám đúng các schema bên dưới). Bỏ biến này khi backend sẵn sàng.

Ký hiệu: tất cả đường dẫn có tiền tố `/api/v1`. "Auth" là gửi `Authorization: Bearer <JWT>`.
Schema tham chiếu `backend/app/schemas/*.py`. Lỗi trả dạng `{"detail": "<thông báo tiếng Việt>"}`
(`AppError`) để frontend hiển thị nguyên văn.

## 0. Đã chạy được (không cần làm)

| Method | Path | Ghi chú |
|---|---|---|
| POST | `/auth/register` | body `RegisterRequest` -> `TokenResponse` |
| POST | `/auth/login` | body `LoginRequest` -> `TokenResponse` |
| GET | `/auth/me` | -> `UserOut` |
| GET | `/health` | `{"status":"ok"}` |

## 1. Endpoint đã khai báo, chưa cài đặt (`NotImplementedError`)

### 1.1 Auth

| Method | Path | Request | Response | Frontend dùng ở |
|---|---|---|---|---|
| POST | `/auth/change-password` | body `ChangePasswordRequest` `{old_password, new_password(min 8)}` | `{"detail"/"message": str}` (frontend chỉ cần 2xx). Sai mật khẩu cũ: 401 `"Mật khẩu cũ không đúng."` | Trang Tài khoản |

### 1.2 Projects

| Method | Path | Request | Response | Ghi chú |
|---|---|---|---|---|
| GET | `/projects` | - | `list[ProjectOut]` `{id, name, owner_id, created_at}` | Admin thấy tất cả, user chỉ thấy của mình |
| POST | `/projects` | `ProjectCreate` `{name(1..255)}` | `ProjectOut` | |
| GET | `/projects/{project_id}` | - | `ProjectOut` | 403 nếu không phải owner/admin. Frontend dùng để lấy tên project khi mở dataset theo ID |
| PUT | `/projects/{project_id}` | `ProjectUpdate` `{name}` | `ProjectOut` | |
| DELETE | `/projects/{project_id}` | - | `{"message": str}` | Frontend hỏi xác nhận trước khi gọi |

### 1.3 Datasets

| Method | Path | Request | Response | Ghi chú |
|---|---|---|---|---|
| POST | `/datasets/upload` | query `project_id: int`; multipart field `file` | `DatasetUploadResponse` `{dataset: DatasetOut, first_version: DatasetVersionOut, sheet_names: list[str], preview_rows: list[{row_index, values: dict[str,str\|null]}]}` | Vượt `MAX_UPLOAD_MB`: 4xx kèm thông báo. Excel nhiều sheet: trả `sheet_names` |
| GET | `/datasets/{dataset_id}` | - | `DatasetOut` | Dùng cho ô "Mở dataset theo ID" |
| GET | `/datasets/{dataset_id}/versions` | - | `list[DatasetVersionOut]` | Frontend tự sắp xếp theo `version_number` |
| POST | `/datasets/{dataset_id}/select-sheet` | query `sheet_name: str` | `DatasetUploadResponse` | |

### 1.4 Profiling

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/profiling/{version_id}/run` | - | `ProfilingResult` `{version_id, columns: list[SchemaProfileOut]}` |
| GET | `/profiling/{version_id}` | - | `ProfilingResult` (404 nếu chưa chạy; frontend khi đó gọi `run`) |

`GET /profiling/{version_id}` phải trả **404** khi chưa chạy profiling: frontend khi đó tự gọi `POST .../run`. `detected_format` là chuỗi hiển thị nguyên văn (cột ngày). Frontend không dùng `QualityReportOut.issue_summary` (chưa có định dạng cố định).

`SchemaProfileOut`: `id, version_id, column_name, column_index, inferred_type, null_count,
unique_count, null_ratio, unique_ratio, min_value, max_value, mean_value, sample_values, detected_format,
created_at`. Frontend dùng `null_ratio`, `inferred_type`, `unique_count`, `sample_values` để vẽ bảng và biểu đồ.

### 1.5 Mapping cột

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/mapping/{version_id}/suggest` | body là **mảng JSON** `list[str]` (các cột chuẩn), ví dụ `["ho_ten","so_dien_thoai"]` | `dict[str, str\|null]` (cột nguồn -> cột đích, `null` nếu không khớp) |

Frontend dựa vào: **khóa = tên cột nguồn** (đủ mọi cột của version, đúng thứ tự), **giá trị = tên cột chuẩn hoặc `null`** (khớp với `match_columns(source_columns, target_schema)`). Frontend không có endpoint lưu mapping: mapping được xác nhận sẽ thành các bước rule `rename_column` (`column` = tên cũ, `params.new_name` = tên mới) đi qua `POST /preview` rồi `POST /versions/{dataset_id}/apply`.

### 1.6 Suggestions

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/suggestions/generate` | `SuggestionGenerateRequest` `{version_id}` | `list[SuggestionOut]` |
| GET | `/suggestions/by-version/{version_id}` | - | `list[SuggestionOut]` |
| POST | `/suggestions/{suggestion_id}/decision` | `{decision: "accepted"\|"rejected"}` | `SuggestionOut` |

`SuggestionOut`: `id, version_id, issue_id, suggestion_type(fix|rule|column_mapping),
source(ai|rule_engine), target_column, proposed_rule: RuleSet, explanation, confidence(0..1|null),
status(pending|accepted|rejected), reviewed_by, reviewed_at, created_at`.

### 1.7 Preview và Versions

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/preview` | `PreviewRequest` `{version_id, rule_set: RuleSet, sample_rows=50}` | `PreviewResult` `{version_id, before_rows, after_rows, diffs: [{row_index, column, before, after}], affected_row_count}` |
| POST | `/versions/{dataset_id}/apply` | body `RuleSet` | `DatasetVersionOut` (version mới) |
| POST | `/versions/{dataset_id}/undo` | - | `DatasetVersionOut` |
| POST | `/versions/{dataset_id}/redo` | - | `DatasetVersionOut` |
| POST | `/versions/{dataset_id}/restore/{version_id}` | - | `DatasetVersionOut` |

Định dạng `RuleSet`/`RuleStep` giữ nguyên `app/schemas/rule.py` (frontend không đổi).

Hợp đồng frontend (trang Gợi ý làm sạch) dựa vào:
- `POST /suggestions/generate` **thay thế** gợi ý cũ của cùng `version_id` (không cộng dồn); trả `[]` khi không có gì cần làm sạch (frontend hiện "Dữ liệu đã sạch"). Gợi ý đã sinh được đọc lại bằng `GET /suggestions/by-version/{id}`.
- `POST /suggestions/{id}/decision` cho phép đổi quyết định nhiều lần (accepted <-> rejected). Chấp nhận **không** áp dụng gì: chỉ `apply` mới tạo version.
- `POST /preview`: `before_rows` là mẫu `sample_rows` dòng đầu (mọi giá trị dạng chuỗi, ô thiếu là `""`); `after_rows` là kết quả trên đúng mẫu đó, **giữ nguyên thứ tự dòng** (dòng bị xóa chỉ biến mất); `diffs[].row_index` là vị trí 0-based trong `before_rows`; `diffs` chỉ gồm cột có ở cả trước và sau (cột mới/đổi tên không có diff). Frontend dùng các quy ước này để tô màu ô thay đổi.
- `POST /versions/{dataset_id}/apply`: body là `RuleSet` `{"steps": [...]}`; áp lên `current_version_id`, trả `DatasetVersionOut` của version mới (`parent_version_id` = version cũ); `422` + `detail` tiếng Việt khi rule sai (cột không tồn tại, op ngoài danh sách, danh sách bước rỗng).
- Thứ tự bước frontend gửi: các bước làm sạch trước, các bước `rename_column` (từ trang Mapping) **sau cùng**, vì gợi ý được sinh theo tên cột hiện tại. Frontend gộp các
`steps` của các gợi ý đã chấp nhận thành một `RuleSet` rồi gọi `preview` -> `apply`.
Cần: `undo`/`redo` trả 4xx có thông báo rõ khi không còn bước để hoàn tác/làm lại
(frontend hiển thị `detail` nguyên văn và tắt nút tương ứng).

### 1.8 Quality và Export

| Method | Path | Response |
|---|---|---|
| GET | `/quality/{version_id}` | `QualityReportOut` `{id, version_id, overall_score, completeness, uniqueness, validity, consistency, issue_summary, created_at}` (điểm 0..100) |
| GET | `/export/{version_id}/csv` | `StreamingResponse` CSV UTF-8-BOM, `Content-Disposition` có tên file |
| GET | `/export/{version_id}/excel` | `StreamingResponse` .xlsx nhiều sheet kèm báo cáo chất lượng |

### 1.9 Audit

| Method | Path | Response | Ghi chú |
|---|---|---|---|
| GET | `/audit/me` | `list[AuditLogOut]` | |
| GET | `/audit/all` | `list[AuditLogOut]` | Chỉ admin |

`AuditLogOut`: `id, user_id, project_id, entity_type, entity_id, action, old_value, new_value, ip_address, created_at`.
Frontend hiển thị mới nhất lên đầu (nên trả sẵn `created_at DESC`).

### 1.10 Admin (chỉ admin)

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/admin/users` | - | `list[UserOut]` `{id, email, full_name, role, is_active, created_at}` |
| PATCH | `/admin/users/{user_id}` | `UserUpdateByAdmin` `{role?: "admin"\|"user", is_active?: bool}` | `UserOut` |
| POST | `/admin/users/{user_id}/reset-password` | - | `{"new_password"?: str, "message": str}`. **Cần quyết định**: trả mật khẩu tạm để admin báo cho user, hay gửi kênh khác. Frontend hiển thị `new_password` nếu có |
| GET | `/admin/stats` | - | `SystemStatsOut` `{total_users, total_admins, active_users, total_projects, total_datasets, total_ai_calls, average_quality_score}` |

### 1.11 Rules (rule template)

Frontend giai đoạn này **chưa dùng** `/rules/*`; còn khai báo, chưa cài đặt:
`GET|POST /rules/by-project/{project_id}`, `DELETE /rules/{rule_id}`.

## 2. Endpoint frontend cần nhưng backend CHƯA CÓ

| # | Đề xuất | Lý do / frontend dùng ở | Tạm thời frontend làm gì |
|---|---|---|---|
| 1 | `GET /projects/{project_id}/datasets` -> `list[DatasetOut]` (hoặc `GET /datasets?project_id=`) | Dashboard (số dataset), chọn lại dataset sau khi tải lại trang | Ô "Mở dataset theo ID" (`TODO` trong `components/`), dựa vào `GET /datasets/{id}` |
| 2 | `GET /profiling/{version_id}/issues` -> danh sách lỗi (`data_issues`: cột, loại lỗi, mức độ nghiêm trọng, số dòng, ví dụ) | Trang Tổng quan dữ liệu ("lỗi đã phát hiện"), màu mức độ ở thẻ gợi ý (hiện `SuggestionOut` chỉ có `issue_id`) | Không hiển thị mục lỗi chi tiết, chỉ có thống kê cột |
| 3 | `GET /datasets/{dataset_id}/versions/{version_id}/rows?offset=&limit=` -> hàng dữ liệu | Xem dữ liệu của một version (ngoài `preview_rows` lúc upload) | Dùng `POST /preview` với `RuleSet` rỗng để lấy mẫu |
| 4 | `GET/PUT /projects/{id}/column-mappings` (bảng `column_mappings`, có cột `confirmed`) | Lưu/xác nhận mapping | Xác nhận mapping = tạo bước `rename_column` rồi `preview`/`apply` |
| 5 | Nguồn **schema chuẩn** của project (ví dụ `GET /projects/{id}/target-schema`) | Nhập sẵn danh sách cột chuẩn cho `/mapping/{version_id}/suggest` | Người dùng tự nhập danh sách cột đích |
| 6 | `GET /projects` kèm `dataset_count` và `average_quality_score` (hoặc endpoint tổng hợp) | Dashboard, tránh gọi lẻ từng dataset | Chỉ hiển thị khi có dữ liệu, ẩn nếu thiếu |

## 3. Quy ước frontend đang dựa vào

- Thông báo lỗi tiếng Việt nằm ở `detail` (chuỗi). Lỗi 422 của Pydantic (`detail` là danh sách) được frontend rút gọn.
- Lỗi 5xx: frontend ẩn nội dung và chỉ hiện "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng"
  (chi tiết kỹ thuật nằm trong mục thu gọn). Khi chưa cài đặt hãy ưu tiên trả `501` + `detail` rõ nghĩa thay vì 500.
- Thời gian là ISO 8601 (có múi giờ); frontend hiển thị dạng `dd/MM/yyyy HH:mm`.
- Không đổi: schema DB, định dạng rule JSON (`RuleSet`), quyền `admin`/`user`.

## 4. Ghi chú về mock

`frontend/mock_api.py` (cùng `mock_data.py`, `mock_profiling.py`, `mock_mapping.py`, `mock_rules.py`,
`mock_suggest.py`) chỉ là **tài liệu tham khảo hành vi** và công cụ để dựng giao diện khi backend
chưa xong. Backend:

- **Phải tự cài Rule Engine** (và profiling, điểm chất lượng, gợi ý mapping, sinh gợi ý...) theo
  `docs/rule_dsl.md`, `docs/quality_score.md` và các schema trong `backend/app/schemas`.
- **KHÔNG import hay sao chép trực tiếp** code từ `frontend/`. Mock dùng thuật toán đơn giản để đủ
  demo (ví dụ suy luận kiểu theo regex, phát hiện biến thể tên bằng bỏ dấu), không phải đặc tả.
- Nếu mock và `docs/` mâu thuẫn, `docs/` và schema backend là nguồn đúng; hãy báo để sửa mock.
- Mock không có trong ảnh Docker chạy thật: chế độ này chỉ bật bằng biến `FRONTEND_MOCK=1`.

