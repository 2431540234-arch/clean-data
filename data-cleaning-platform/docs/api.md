# Tài liệu API

> TODO: hoàn thiện tài liệu này (hoặc tham chiếu Swagger UI tại `/docs`). Dàn ý các mục:

## 1. Xác thực (`/api/v1/auth`)

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/change-password`.

## 2. Quản trị (`/api/v1/admin`, chỉ admin)

- `GET /admin/users`, `PATCH /admin/users/{id}`, `POST /admin/users/{id}/reset-password`,
  `GET /admin/stats`.

## 3. Project (`/api/v1/projects`)

- `GET /projects`, `POST /projects`, `GET /projects/{id}`, `PUT /projects/{id}`,
  `DELETE /projects/{id}`.

## 4. Dataset (`/api/v1/datasets`)

- `POST /datasets/upload`, `GET /datasets/{id}`, `GET /datasets/{id}/versions`,
  `POST /datasets/{id}/select-sheet`.

## 5. Profiling (`/api/v1/profiling`)

- `POST /profiling/{version_id}/run`, `GET /profiling/{version_id}`.

## 6. Gợi ý (`/api/v1/suggestions`)

- `POST /suggestions/generate`, `GET /suggestions/by-version/{version_id}`,
  `POST /suggestions/{id}/decision`.

## 7. Mapping cột (`/api/v1/mapping`)

- `POST /mapping/{version_id}/suggest`.

## 8. Preview (`/api/v1/preview`)

- `POST /preview`.

## 9. Version / undo-redo (`/api/v1/versions`)

- `POST /versions/{dataset_id}/apply`, `.../undo`, `.../redo`,
  `.../restore/{version_id}`.

## 10. Rule template (`/api/v1/rules`)

- `GET /rules/by-project/{project_id}`, `POST /rules/by-project/{project_id}`,
  `DELETE /rules/{id}`.

## 11. Quality (`/api/v1/quality`)

- `GET /quality/{version_id}`.

## 12. Export (`/api/v1/export`)

- `GET /export/{version_id}/csv`, `GET /export/{version_id}/excel`.

## 13. Audit log (`/api/v1/audit`)

- `GET /audit/me`, `GET /audit/all` (chỉ admin).

## 14. Health check

- `GET /health` -> `{"status": "ok"}`.
