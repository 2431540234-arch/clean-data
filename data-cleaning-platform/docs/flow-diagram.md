# Sơ đồ hệ thống – Data Cleaning Platform

Tài liệu tập hợp các sơ đồ của dự án: kiến trúc, use case, ERD và các luồng xử lý.
Mọi sơ đồ viết bằng [Mermaid](https://mermaid.js.org/), xem trực tiếp trên GitHub hoặc bằng
preview Markdown của VS Code (cài thêm extension "Markdown Preview Mermaid Support" nếu chưa hiện hình).
Muốn đưa vào slide, mở sơ đồ trên <https://mermaid.live> rồi xuất PNG/SVG.

Mục lục: [1. Kiến trúc](#1-kiến-trúc-tổng-thể) · [2. Use case](#2-use-case) · [3. ERD](#3-erd-mô-hình-dữ-liệu) ·
[4. Các luồng](#4-các-luồng-xử-lý) · [5. Triển khai](#5-sơ-đồ-triển-khai) · [6. Trạng thái cài đặt](#6-trạng-thái-cài-đặt)

> **Cách đọc:** các sơ đồ mô tả **thiết kế mục tiêu** của hệ thống. Tên route, bảng, cột và cổng đã được
> đối chiếu với mã nguồn. Phần nào đã chạy được và phần nào còn là khung (stub) xem ở
> [mục 6](#6-trạng-thái-cài-đặt). Mọi đường dẫn API có tiền tố `/api/v1` (Swagger: `http://localhost:8000/docs`).

---

## 1. Kiến trúc tổng thể

```mermaid
flowchart LR
    U([Người dùng<br/>trình duyệt]) -->|HTTP| FE[Frontend<br/>Streamlit + Plotly<br/>:8501]
    FE -->|REST/JSON<br/>httpx + JWT| BE[Backend<br/>FastAPI + Uvicorn<br/>:8000]

    subgraph BE_INNER [Backend – các lớp]
        direction TB
        API["api/v1 routers<br/>(auth · admin · projects · datasets · profiling<br/>suggestions · mapping · preview · versions<br/>rules · quality · export · audit)"]
        CORE["core<br/>config · security JWT/bcrypt · deps<br/>permissions · exceptions · logging"]
        SVC["services<br/>ingestion · profiling · detectors · mapping<br/>ai · rules · preview · versioning<br/>quality · report · export · storage · audit"]
        WK[workers<br/>tác vụ nền]
        REPO[repositories]
        MODEL["models<br/>SQLAlchemy 2.0"]
        API --> SVC
        API -.-> CORE
        SVC --> REPO
        WK --> SVC
        REPO --> MODEL
    end
    BE --- API

    MODEL --> PG[("PostgreSQL 16<br/>16 bảng metadata:<br/>user, project, dataset, version, issue,<br/>suggestion, rule, job, audit log...")]
    SVC --> ST[("Object Storage S3<br/>file gốc + mỗi phiên bản Parquet")]
    SVC --> AI{{AI Provider<br/>OpenAI / Claude}}
    ALB[Alembic<br/>migration 0001] --> PG
```

**Nguyên tắc cốt lõi:** AI chỉ sinh **rule JSON** (theo DSL `RuleSet`); chỉ **Rule Engine (Pandas)** mới sửa dữ
liệu thật, và không bao giờ `exec()` mã do AI sinh. PostgreSQL **chỉ lưu metadata**; dữ liệu từng dòng nằm
trong file Parquet trên object storage (`dataset_versions.storage_path`).

---

## 2. Use case

```mermaid
flowchart LR
    User([Người dùng])
    Admin([Quản trị viên])
    AIP([AI Provider])

    subgraph SYS [Data Cleaning Platform]
        UC1(UC1 Đăng ký / đăng nhập)
        UC2(UC2 Tạo project, upload CSV/Excel)
        UC3(UC3 Xem profiling schema)
        UC4(UC4 Xem lỗi phát hiện được)
        UC5(UC5 Nhận gợi ý rule, giải thích lỗi,<br/>mapping tên cột)
        UC6(UC6 Xem preview trước/sau)
        UC7(UC7 Xác nhận áp dụng rule)
        UC8(UC8 Undo / redo / khôi phục phiên bản)
        UC9(UC9 Xem điểm chất lượng dữ liệu)
        UC10(UC10 Xuất dữ liệu sạch CSV/Excel)
        UC11(UC11 Xem audit log)
        UC12(UC12 Quản lý user, thống kê hệ thống)
        UC13(UC13 Lưu rule mẫu theo project)
        UC14(UC14 Xem thông tin, đổi mật khẩu)
    end

    User --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC13 & UC14
    Admin --- UC1 & UC11 & UC12 & UC14
    UC5 --- AIP
    UC5 -. include .-> UC4
    UC7 -. include .-> UC6
```

| Vai trò | Quyền |
|---|---|
| **User** | Làm việc trên project/dataset **của chính mình**; xem audit log của mình (`GET /audit/me`) |
| **Admin** | Thấy mọi project; quản lý user (khóa/mở, đổi quyền, reset mật khẩu), xem thống kê và toàn bộ audit log (`GET /audit/all`) |
| **AI Provider** | Hệ thống ngoài, chỉ trả về gợi ý dạng JSON; không được sửa dữ liệu |

Quyền project do `app.core.permissions.ensure_can_access_project` kiểm tra (admin hoặc `projects.owner_id`);
bảng `project_members` đã có sẵn để mở rộng chia sẻ project, hiện chưa dùng để kiểm quyền.

---

## 3. ERD (mô hình dữ liệu)

Schema đầy đủ (**16 bảng nghiệp vụ**), sơ đồ ER dạng Mermaid, hành vi khi xóa và luồng dữ liệu qua các
bảng nằm ở **[database.md](database.md)** (nguồn: [backend/app/models/](../backend/app/models/) và
migration `0001`). Phiên bản đang dùng của dataset được xác định bởi
`datasets.current_version_id`, không còn cờ `is_current`.

Tóm tắt các nhóm bảng:

| Nhóm | Bảng |
|---|---|
| Người dùng | `users`, `project_members` |
| Dữ liệu | `projects`, `datasets`, `dataset_versions`, `schema_profiles`, `column_mappings` |
| Lỗi và gợi ý | `data_issues`, `suggestions`, `rules`, `cleaning_operations` |
| Chất lượng, xuất file | `quality_reports`, `exports` |
| Tác vụ nền, AI, nhật ký | `jobs`, `ai_requests`, `audit_logs` |

---

## 4. Các luồng xử lý

### 4.1 Luồng tổng quát (end-to-end)

```mermaid
flowchart TD
    A([Bắt đầu]) --> B[Đăng ký / đăng nhập → JWT]
    B --> C[Tạo project]
    C --> D[Upload file CSV/Excel]
    D --> E[Ingestion:<br/>dò encoding, delimiter, header]
    E --> F[Lưu file gốc + version 1 Parquet<br/>datasets + dataset_versions]
    F --> G[Profiling schema<br/>→ schema_profiles]
    G --> H[Detectors phát hiện lỗi<br/>→ data_issues]
    H --> I[AI gợi ý rule JSON + giải thích<br/>→ suggestions, ai_requests]
    I --> J{Validator<br/>hợp lệ?}
    J -- Không --> I2[Loại bỏ gợi ý] --> I
    J -- Có --> K[Người dùng chọn rule]
    K --> L[Preview dry-run<br/>trước / sau]
    L --> M{Xác nhận<br/>áp dụng?}
    M -- Không --> K
    M -- Có --> N[Rule Engine áp dụng bằng Pandas]
    N --> O[Version mới + cleaning_operations<br/>+ audit_logs]
    O --> P[Tính điểm chất lượng<br/>→ quality_reports]
    P --> Q{Cần làm tiếp?}
    Q -- Có --> H
    Q -- Undo/Redo --> R[Đổi datasets.current_version_id] --> P
    Q -- Không --> S[Export CSV / Excel<br/>→ exports]
    S --> T([Kết thúc])
```

File lớn: profiling và phát hiện lỗi chạy nền (`app/workers`), tiến độ lưu ở bảng `jobs`
(`pending → running → done | failed`, `progress` 0–100) để giao diện hỏi lại trạng thái.

### 4.2 Đăng ký, đăng nhập và phân quyền

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant FE as Streamlit
    participant BE as FastAPI
    participant DB as PostgreSQL

    U->>FE: Nhập email, mật khẩu
    FE->>BE: POST /api/v1/auth/login
    BE->>DB: Tìm user theo email
    DB-->>BE: User + password_hash
    BE->>BE: Kiểm tra bcrypt, is_active
    alt Hợp lệ
        BE-->>FE: JWT access token (hết hạn sau 60 phút)
        FE->>FE: Lưu token trong session
    else Sai thông tin / tài khoản bị khóa
        BE-->>FE: 401 Unauthorized
    end
    U->>FE: Thao tác khác
    FE->>BE: Request + Authorization: Bearer JWT
    BE->>BE: get_current_user giải mã JWT, kiểm tra user còn tồn tại và is_active
    alt Token sai / hết hạn / user bị khóa
        BE-->>FE: 401
    else Route chỉ-admin và user không phải admin, hoặc không phải chủ project
        BE-->>FE: 403 Forbidden
    else Đủ quyền
        BE-->>FE: 200 dữ liệu
    end
```

Đăng ký (`POST /auth/register`) luôn tạo role `user` (không tự đăng ký admin) và trả luôn token.
Admin đầu tiên tạo bằng `scripts/create_admin.py`.

### 4.3 Upload và ingestion

```mermaid
flowchart TD
    A[POST /api/v1/datasets/upload<br/>kèm project_id] --> A2{Có quyền<br/>với project?}
    A2 -- Không --> X0[403 Forbidden]
    A2 -- Có --> B{Kích thước<br/>≤ MAX_UPLOAD_MB<br/>mặc định 50?}
    B -- Không --> X1[Từ chối file quá lớn]
    B -- Có --> C{Định dạng?}
    C -- CSV --> D[charset-normalizer dò encoding<br/>dò delimiter · dò dòng header]
    C -- XLSX/XLS --> E[openpyxl / xlrd<br/>liệt kê sheet]
    E --> F{Nhiều sheet?}
    F -- Có --> G[POST /datasets/id/select-sheet<br/>người dùng chọn sheet]
    F -- Không --> H
    G --> H
    D --> H[Đọc thành DataFrame dtype=str]
    H --> I[Lưu file gốc lên Object Storage]
    I --> J[Ghi Parquet → dataset_versions v1<br/>datasets.current_version_id = v1<br/>datasets: file_type, file_size, encoding, sheet_name]
    J --> K[Ghi audit log: dataset.upload]
```

### 4.4 Profiling và phát hiện lỗi

```mermaid
flowchart LR
    V[(Version hiện tại<br/>Parquet)] --> P["Profiler POST /profiling/version_id/run<br/>suy luận kiểu, null/unique,<br/>min/max/mean, định dạng, giá trị mẫu"]
    P --> SP[(schema_profiles<br/>null_count, unique_count,<br/>null_ratio, unique_ratio)]
    V --> D{Detectors}
    D --> D1[missing<br/>null token]
    D --> D2[duplicates<br/>chính xác + rapidfuzz]
    D --> D3[outliers<br/>IQR / Z-score]
    D --> D4[dates<br/>dateutil]
    D --> D5[phones<br/>phonenumbers]
    D --> D6[emails<br/>email-validator]
    D --> D7[whitespace_case<br/>khoảng trắng / hoa thường]
    D --> D8[inconsistency<br/>giá trị không nhất quán]
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 --> R[(data_issues<br/>issue_type, severity, status)]
```

Ánh xạ detector → `data_issues.issue_type`:

| Detector | `issue_type` |
|---|---|
| missing | `missing` |
| duplicates | `duplicate` |
| outliers | `outlier` |
| dates, phones, emails | `invalid_format` |
| whitespace_case, inconsistency | `inconsistent` |
| suy luận kiểu (profiling) | `type_mismatch` |

`severity` ∈ `low` / `medium` / `high`; `row_index = NULL` nghĩa là lỗi ở mức cả cột; `status` ∈
`open` / `fixed` / `ignored`.

### 4.5 AI gợi ý rule và mapping cột

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant BE as FastAPI
    participant M as masking.py
    participant AI as AI Provider
    participant V as Validator
    participant DB as PostgreSQL

    U->>BE: POST /api/v1/suggestions/generate
    BE->>BE: Chạy detectors → gợi ý từ rule (source = rule_engine)
    BE->>M: Che dữ liệu nhạy cảm (mẫu giá trị)
    M-->>BE: Dữ liệu đã che
    BE->>AI: Prompt + schema + lỗi (structured output / tool calling)
    Note over BE,AI: tenacity tự thử lại khi lỗi mạng / rate limit
    AI-->>BE: JSON: rule + giải thích + confidence
    BE->>DB: Ghi ai_requests (provider, model, token, độ trễ; không lưu API key hay dữ liệu)
    BE->>V: Kiểm tra theo DSL (op cho phép, cột tồn tại)
    alt Hợp lệ
        V-->>BE: OK
        BE->>DB: Lưu suggestions (source = ai, status = pending, issue_id nếu có)
        BE-->>U: Danh sách gợi ý + giải thích dễ hiểu
    else Không hợp lệ
        V-->>BE: Loại bỏ
        BE-->>U: Chỉ trả các gợi ý hợp lệ
    end
    U->>BE: POST /api/v1/suggestions/{id}/decision (accepted / rejected)
    BE->>DB: Cập nhật status, reviewed_by, reviewed_at
```

`suggestions.suggestion_type` ∈ `fix` / `rule` / `column_mapping`; `confidence` từ 0 đến 1. Mức độ nghiêm
trọng không nằm ở gợi ý mà ở lỗi gắn qua `issue_id` (`data_issues.severity`).

**Mapping tên cột** (`POST /api/v1/mapping/{version_id}/suggest`, body là danh sách cột chuẩn):

```mermaid
flowchart LR
    C[Tên cột trong file] --> N["Chuẩn hóa<br/>bỏ dấu Unidecode, chữ thường"]
    N --> T1["Tầng 1: rapidfuzz so khớp<br/>column_synonyms.json"]
    T1 --> Q{Đủ chắc chắn?}
    Q -- Có --> OUT[Gợi ý mapping]
    Q -- Không --> T2["Tầng 2: hỏi AI<br/>chỉ với cột chưa khớp"]
    T2 --> OUT
    OUT --> CM[(column_mappings<br/>confirmed khi người dùng duyệt)]
```

### 4.6 Preview và áp dụng rule

```mermaid
flowchart TD
    A["POST /api/v1/preview<br/>{version_id, rule_set, sample_rows}"] --> B[Validate RuleSet<br/>Pydantic + validator]
    B --> C[Đọc DataFrame từ Parquet]
    C --> D[Rule Engine dry_run<br/>trên BẢN SAO, mẫu sample_rows dòng]
    D --> E["PreviewResult: before_rows, after_rows,<br/>diffs từng ô, affected_row_count"]
    E --> F{Người dùng<br/>xác nhận?}
    F -- Không --> Z([Dừng, dữ liệu giữ nguyên])
    F -- Có --> G["POST /api/v1/versions/dataset_id/apply<br/>body: RuleSet"]
    G --> H[Rule Engine apply_rules<br/>áp dụng thật, từng bước]
    H --> I[Ghi Parquet mới → dataset_versions v+1<br/>version_number + 1, parent_version_id = v]
    I --> J[Đặt datasets.current_version_id = v+1]
    J --> K[Ghi cleaning_operations<br/>from_version → to_version, rows_affected<br/>+ audit_logs: old_value, new_value]
    K --> L[Tính quality_reports của v+1]
```

### 4.7 Phiên bản, undo, redo, khôi phục

```mermaid
stateDiagram-v2
    direction LR
    [*] --> V1: upload
    V1 --> V2: apply rule
    V2 --> V3: apply rule
    V3 --> V2: undo
    V2 --> V3: redo
    V3 --> V1: restore v1
    V2 --> V4: apply rule (sau undo, nhánh mới)
    note right of V3
        Mỗi phiên bản = 1 file Parquet
        + 1 dòng dataset_versions
        + 1 dòng cleaning_operations
        + 1 dòng audit_logs
    end note
```

Undo, redo và restore **không tạo hay xóa phiên bản**; chúng chỉ đổi con trỏ `datasets.current_version_id`.
Chỉ `apply` mới tạo phiên bản mới.

| Endpoint | Hành động |
|---|---|
| `POST /api/v1/versions/{dataset_id}/undo` | Đặt `current_version_id` về `parent_version_id` của phiên bản hiện tại |
| `POST /api/v1/versions/{dataset_id}/redo` | Tiến tới phiên bản con gần nhất (`version_number` lớn nhất) của phiên bản hiện tại |
| `POST /api/v1/versions/{dataset_id}/restore/{version_id}` | Đặt `current_version_id` = một phiên bản bất kỳ trong lịch sử |
| `GET /api/v1/datasets/{dataset_id}/versions` | Danh sách phiên bản (cây phiên bản qua `parent_version_id`) |

### 4.8 Điểm chất lượng và xuất file

```mermaid
flowchart LR
    V[(Version hiện tại)] --> Q["quality.py<br/>tính các chỉ số"]
    Q --> M1["Đầy đủ<br/>completeness × 0.3"]
    Q --> M2["Hợp lệ<br/>validity × 0.3"]
    Q --> M3["Duy nhất<br/>uniqueness × 0.2"]
    Q --> M4["Nhất quán<br/>consistency × 0.2"]
    M1 & M2 & M3 & M4 --> S[Điểm tổng 0–100<br/>→ quality_reports<br/>mỗi version một báo cáo]
    S --> UI[Plotly: đồng hồ điểm,<br/>biểu đồ missing, phân bố]
    V --> E{Export}
    E -->|GET /api/v1/export/version_id/csv| C["File CSV sạch<br/>UTF-8 BOM"]
    E -->|GET /api/v1/export/version_id/excel| X["File Excel sạch<br/>nhiều sheet, kèm báo cáo chất lượng"]
    C & X --> EX[(exports<br/>format, file_size, exported_by)]
```

Đọc điểm: `GET /api/v1/quality/{version_id}`. Chi tiết công thức: [quality_score.md](quality_score.md)
(công thức tổng hợp đã có, phần chi tiết từng chỉ số còn TODO).

### 4.9 Quản trị (Admin)

```mermaid
flowchart TD
    A([Admin đăng nhập]) --> B{require_admin}
    B -- Không phải admin --> X[403 Forbidden]
    B -- Admin --> C[GET /api/v1/admin/users<br/>danh sách user]
    C --> D[PATCH /api/v1/admin/users/id<br/>khóa/mở, đổi role]
    C --> E[POST /api/v1/admin/users/id/reset-password]
    B --> F[GET /api/v1/admin/stats<br/>thống kê hệ thống]
    B --> G[GET /api/v1/audit/all<br/>toàn bộ audit log]
```

### 4.10 Bảng tổng hợp API (`/api/v1`)

| Nhóm | Endpoint |
|---|---|
| auth | `POST /auth/register` · `POST /auth/login` · `GET /auth/me` · `POST /auth/change-password` |
| admin | `GET /admin/users` · `PATCH /admin/users/{user_id}` · `POST /admin/users/{user_id}/reset-password` · `GET /admin/stats` |
| projects | `GET /projects` · `POST /projects` · `GET/PUT/DELETE /projects/{project_id}` |
| datasets | `POST /datasets/upload` · `GET /datasets/{id}` · `GET /datasets/{id}/versions` · `POST /datasets/{id}/select-sheet` |
| profiling | `POST /profiling/{version_id}/run` · `GET /profiling/{version_id}` |
| suggestions | `POST /suggestions/generate` · `GET /suggestions/by-version/{version_id}` · `POST /suggestions/{id}/decision` |
| mapping | `POST /mapping/{version_id}/suggest` |
| preview | `POST /preview` |
| versions | `POST /versions/{dataset_id}/apply` · `/undo` · `/redo` · `/restore/{version_id}` |
| rules | `GET/POST /rules/by-project/{project_id}` · `DELETE /rules/{rule_id}` |
| quality | `GET /quality/{version_id}` |
| export | `GET /export/{version_id}/csv` · `GET /export/{version_id}/excel` |
| audit | `GET /audit/me` · `GET /audit/all` (admin) |

Ngoài ra: `GET /health` (không có tiền tố `/api/v1`) dùng cho healthcheck.

---

## 5. Sơ đồ triển khai

### 5.1 Chạy cục bộ (Docker Compose)

```mermaid
flowchart LR
    subgraph HOST [Máy dev]
        B[Trình duyệt] -->|localhost:8501| FE
        B -->|localhost:8000/docs| BE
        subgraph DC [docker compose]
            FE[dcp_frontend<br/>Streamlit :8501]
            BE[dcp_backend<br/>FastAPI :8000<br/>chạy alembic upgrade head]
            PG[(dcp_postgres<br/>postgres:16<br/>DB data_cleaning<br/>+ data_cleaning_test)]
            FE -->|BACKEND_URL=http://backend:8000| BE
            BE -->|postgres:5432| PG
        end
        PG -.->|"host port POSTGRES_PORT<br/>(mặc định 5432, máy dev đặt 5434)"| H5434[DBeaver / psql]
    end
    BE --> EXT1{{AI API}}
    BE --> EXT2[(Object Storage<br/>cấu hình bằng STORAGE_*)]
```

Thứ tự khởi động (có healthcheck): `postgres` (healthy) → `backend` (healthy, sau migration) → `frontend`.
Database `data_cleaning_test` do script `docker/postgres-init/01-create-test-db.sql` tạo cho pytest
(chỉ chạy khi volume còn trống).

### 5.2 CI/CD (GitHub Actions)

```mermaid
flowchart LR
    P[Push / Pull request] --> L1
    subgraph TY ["test.yml – Postgres 16 chạy kèm"]
        direction TB
        L1[ruff check] --> L2[black --check] --> L3["Check migrations:<br/>alembic upgrade head<br/>alembic check<br/>alembic downgrade base"] --> L4[pytest]
    end
    M[Push vào main] --> D["Workflow Deploy<br/>(deploy.yml – mới là khung TODO)"]
```

Bước *Check migrations* báo lỗi khi model SQLAlchemy và migration bị lệch nhau
(có thay đổi model nhưng chưa tạo migration).

### 5.3 Môi trường online (mục tiêu của đề tài)

```mermaid
flowchart LR
    U([Người dùng]) -->|HTTPS – URL công khai| FE[Frontend container<br/>Render / Railway / Fly.io]
    FE --> BE[Backend container]
    BE --> DB[(PostgreSQL cloud<br/>Neon / Supabase)]
    BE --> ST[(Object Storage<br/>Supabase Storage / R2)]
    BE --> AI{{OpenAI / Claude API}}
    GH[GitHub] -->|Actions: test → build → deploy| FE
    GH -->|Actions: test → build → deploy| BE
```

> Nền tảng deploy cụ thể chưa được chọn và `deploy.yml` mới là khung; sơ đồ 5.3 sẽ cập nhật khi chốt
> Render/Railway/Fly.io.

---

## 6. Trạng thái cài đặt

Đối chiếu với mã nguồn (cập nhật 04/11/2026). Ký hiệu: ✅ đã chạy được và có test · 🚧 chưa làm.

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng: Docker Compose, healthcheck, `/health`, Swagger `/docs` | ✅ |
| CI `test.yml` (ruff, black, `alembic upgrade/check/downgrade`, pytest backend; ruff + pytest frontend) | ✅ |
| CI `deploy.yml` | 🚧 khung TODO |
| Database: 16 bảng, migration `0001` + `0003` + `0004`, `alembic check` sạch, test migration trên DB trống | ✅ |
| Model SQLAlchemy, schema Pydantic, DSL `RuleSet` + validator rule | ✅ |
| Hạ tầng dùng chung: lưu trữ local/S3, kiểm tra quyền sở hữu (`services/access`), xử lý lỗi, cấu hình an toàn | ✅ |
| Auth: đăng ký, đăng nhập (chặn dò mật khẩu 429), đổi mật khẩu, thu hồi token, `require_admin` | ✅ |
| Ingestion (CSV/Excel, dò encoding/delimiter/dòng tiêu đề, kiểm tra loại file, giới hạn kích thước) | ✅ |
| Profiling + 8 detector (thiếu, trùng, outlier, ngày, SĐT, email, khoảng trắng/hoa thường, biến thể giá trị) | ✅ |
| Mapping cột: tầng 1 (từ điển + rapidfuzz), tầng 2 bằng AI khi có khóa | ✅ |
| Gợi ý làm sạch: theo quy tắc; AI tùy chọn (che dữ liệu cá nhân, kiểm tra JSON, dự phòng về quy tắc) | ✅ |
| Rule Engine: đủ 13 op, preview (diff từng ô), apply / undo / redo / restore, rule template | ✅ |
| Điểm chất lượng (4 tiêu chí), xuất CSV/Excel (chống chèn công thức), xem dòng theo trang | ✅ |
| API: projects, datasets, profiling, suggestions, mapping, preview, versions, rules, quality, export, audit, admin | ✅ (toàn bộ) |
| Audit log: mọi thao tác ghi dữ liệu để lại một dòng cùng giao dịch | ✅ |
| Frontend Streamlit: 12 trang, chạy với backend thật (và chế độ dữ liệu mẫu `FRONTEND_MOCK=1`) | ✅ |
| Worker nền (`workers/tasks.py`), `column_mappings` / `target-schema` (endpoint #4, #5 chưa làm) | 🚧 |
| Deploy online có URL công khai | 🚧 |
