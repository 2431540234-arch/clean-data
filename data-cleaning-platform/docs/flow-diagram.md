# Sơ đồ hệ thống – Data Cleaning Platform

Tài liệu tập hợp các sơ đồ của dự án: kiến trúc, use case, ERD và các luồng xử lý.
Mọi sơ đồ viết bằng [Mermaid](https://mermaid.js.org/), xem trực tiếp trên GitHub hoặc bằng
preview Markdown của VS Code (cài thêm extension "Markdown Preview Mermaid Support" nếu chưa hiện hình).
Muốn đưa vào slide, mở sơ đồ trên <https://mermaid.live> rồi xuất PNG/SVG.

Mục lục: [1. Kiến trúc](#1-kiến-trúc-tổng-thể) · [2. Use case](#2-use-case) · [3. ERD](#3-erd-mô-hình-dữ-liệu) ·
[4. Các luồng](#4-các-luồng-xử-lý) · [5. Triển khai](#5-sơ-đồ-triển-khai)

---

## 1. Kiến trúc tổng thể

```mermaid
flowchart LR
    U([Người dùng<br/>trình duyệt]) -->|HTTP| FE[Frontend<br/>Streamlit + Plotly<br/>:8501]
    FE -->|REST/JSON<br/>httpx + JWT| BE[Backend<br/>FastAPI + Uvicorn<br/>:8000]

    subgraph BE_INNER [Backend – các lớp]
        direction TB
        API[api/v1<br/>routers] --> SVC[services<br/>ingestion · profiling · detectors<br/>ai · rules · preview · versioning<br/>quality · export]
        SVC --> REPO[repositories]
        REPO --> MODEL[models<br/>SQLAlchemy 2.0]
    end
    BE --- API

    MODEL --> PG[(PostgreSQL<br/>user, project, rule,<br/>audit log, metadata)]
    SVC --> ST[(Object Storage S3<br/>file gốc + Parquet)]
    SVC --> AI{{AI Provider<br/>OpenAI / Claude}}
    ALB[Alembic<br/>migration] --> PG
```

**Nguyên tắc cốt lõi:** AI chỉ sinh **rule JSON**; chỉ **Rule Engine (Pandas)** mới sửa dữ liệu thật,
và không bao giờ `exec()` mã do AI sinh.

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
    end

    User --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC13
    Admin --- UC1 & UC11 & UC12
    UC5 --- AIP
    UC5 -. include .-> UC4
    UC7 -. include .-> UC6
```

| Vai trò | Quyền |
|---|---|
| **User** | Làm việc trên project/dataset **của chính mình**; xem audit log của mình |
| **Admin** | Quản lý user (khóa/mở, đổi quyền, reset mật khẩu), xem thống kê và toàn bộ audit log |
| **AI Provider** | Hệ thống ngoài, chỉ trả về gợi ý dạng JSON |

---

## 3. ERD (mô hình dữ liệu)

Schema đầy đủ (16 bảng nghiệp vụ), sơ đồ ER dạng Mermaid, hành vi khi xóa và luồng dữ liệu qua các
bảng nằm ở **[database.md](database.md)** (nguồn: [backend/app/models/](../backend/app/models/) và
các migration `0001`, `0002`). Phiên bản đang dùng của dataset được xác định bởi
`datasets.current_version_id`, không còn cờ `is_current`.

---

## 4. Các luồng xử lý

### 4.1 Luồng tổng quát (end-to-end)

```mermaid
flowchart TD
    A([Bắt đầu]) --> B[Đăng nhập]
    B --> C[Tạo project]
    C --> D[Upload file CSV/Excel]
    D --> E[Ingestion:<br/>dò encoding, delimiter, header]
    E --> F[Lưu file gốc + version 1 Parquet]
    F --> G[Profiling schema]
    G --> H[Detectors phát hiện lỗi]
    H --> I[AI gợi ý rule JSON + giải thích]
    I --> J{Validator<br/>hợp lệ?}
    J -- Không --> I2[Loại bỏ gợi ý] --> I
    J -- Có --> K[Người dùng chọn rule]
    K --> L[Preview dry-run<br/>trước / sau]
    L --> M{Xác nhận<br/>áp dụng?}
    M -- Không --> K
    M -- Có --> N[Rule Engine áp dụng bằng Pandas]
    N --> O[Tạo version mới + ghi audit log]
    O --> P[Tính điểm chất lượng]
    P --> Q{Cần làm tiếp?}
    Q -- Có --> H
    Q -- Undo/Redo --> R[Chuyển version] --> P
    Q -- Không --> S[Export CSV / Excel]
    S --> T([Kết thúc])
```

### 4.2 Đăng ký, đăng nhập và phân quyền

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant FE as Streamlit
    participant BE as FastAPI
    participant DB as PostgreSQL

    U->>FE: Nhập email, mật khẩu
    FE->>BE: POST /auth/login
    BE->>DB: Tìm user theo email
    DB-->>BE: User + password_hash
    BE->>BE: Kiểm tra bcrypt, is_active
    alt Hợp lệ
        BE-->>FE: JWT access token
        FE->>FE: Lưu token trong session
    else Sai thông tin / bị khóa
        BE-->>FE: 401 / 403
    end
    U->>FE: Thao tác khác
    FE->>BE: Request + Authorization: Bearer JWT
    BE->>BE: Dependency giải mã JWT, kiểm tra role
    alt Đủ quyền (và đúng chủ sở hữu dữ liệu)
        BE-->>FE: 200 dữ liệu
    else Không đủ quyền
        BE-->>FE: 403
    end
```

### 4.3 Upload và ingestion

```mermaid
flowchart TD
    A[POST /datasets/upload] --> B{Kích thước<br/>≤ MAX_UPLOAD_MB?}
    B -- Không --> X1[Từ chối file quá lớn]
    B -- Có --> C{Định dạng?}
    C -- CSV --> D[charset-normalizer dò encoding<br/>dò delimiter · dò dòng header]
    C -- XLSX/XLS --> E[openpyxl / xlrd<br/>liệt kê sheet]
    E --> F{Nhiều sheet?}
    F -- Có --> G[POST select-sheet<br/>người dùng chọn sheet]
    F -- Không --> H
    G --> H
    D --> H[Đọc thành DataFrame dtype=str]
    H --> I[Lưu file gốc lên Object Storage]
    I --> J[Ghi Parquet → dataset_versions v1<br/>datasets.current_version_id = v1]
    J --> K[Ghi audit log: upload]
```

### 4.4 Profiling và phát hiện lỗi

```mermaid
flowchart LR
    V[(Version hiện tại<br/>Parquet)] --> P[Profiler<br/>suy luận kiểu, null_ratio,<br/>unique_ratio, giá trị mẫu]
    P --> SP[(schema_profiles)]
    V --> D{Detectors}
    D --> D1[missing<br/>null token]
    D --> D2[duplicates<br/>chính xác + rapidfuzz]
    D --> D3[outliers<br/>IQR / Z-score]
    D --> D4[dates<br/>dateutil]
    D --> D5[phones<br/>phonenumbers]
    D --> D6[emails<br/>email-validator]
    D --> D7[whitespace / case]
    D --> D8[inconsistency<br/>giá trị không nhất quán]
    D1 & D2 & D3 & D4 & D5 & D6 & D7 & D8 --> R[Danh sách lỗi<br/>+ mức độ nghiêm trọng]
```

### 4.5 AI gợi ý rule và mapping cột

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant BE as FastAPI
    participant M as masking.py
    participant AI as AI Provider
    participant V as Validator
    participant DB as PostgreSQL

    U->>BE: POST /suggestions/generate
    BE->>BE: Chạy detectors → gợi ý từ rule (source = rule)
    BE->>M: Che dữ liệu nhạy cảm (mẫu giá trị)
    M-->>BE: Dữ liệu đã che
    BE->>AI: Prompt + schema + lỗi (structured output / tool calling)
    Note over BE,AI: tenacity tự thử lại khi lỗi mạng / rate limit
    AI-->>BE: JSON: rule + giải thích
    BE->>V: Kiểm tra theo DSL (op cho phép, cột tồn tại)
    alt Hợp lệ
        V-->>BE: OK
        BE->>DB: Lưu suggestion (status = pending)
        BE-->>U: Danh sách gợi ý + giải thích dễ hiểu
    else Không hợp lệ
        V-->>BE: Loại bỏ
        BE-->>U: Chỉ trả các gợi ý hợp lệ
    end
    U->>BE: POST /suggestions/{id}/decision (chấp nhận / từ chối)
    BE->>DB: Cập nhật status
```

Mapping tên cột (`POST /api/v1/mapping/{version_id}/suggest`): chuẩn hóa tên cột (bỏ dấu bằng Unidecode, hạ chữ thường),
so khớp với bảng đồng nghĩa `column_synonyms.json` bằng rapidfuzz; phần chưa chắc chắn mới hỏi AI.

### 4.6 Preview và áp dụng rule

```mermaid
flowchart TD
    A[POST /preview<br/>rule_set + version_id] --> B[Validate RuleSet<br/>Pydantic + validator]
    B --> C[Đọc DataFrame từ Parquet]
    C --> D[Rule Engine dry_run<br/>trên BẢN SAO]
    D --> E[Bảng so sánh trước/sau<br/>+ số dòng/ô bị đổi]
    E --> F{Người dùng<br/>xác nhận?}
    F -- Không --> Z([Dừng, dữ liệu giữ nguyên])
    F -- Có --> G[POST /{dataset_id}/apply]
    G --> H[Rule Engine áp dụng thật]
    H --> I[Ghi Parquet mới → dataset_versions v+1<br/>parent_version_id = v]
    I --> J[Đặt datasets.current_version_id = v+1]
    J --> K[Ghi cleaning_operations + audit_logs:<br/>old_value, new_value]
    K --> L[Tính quality_reports]
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
    V3 --> V1: restore (về v1, tạo phiên bản mới)
    V3 --> V4: apply rule
    note right of V3
        Mỗi phiên bản = 1 file Parquet
        + 1 dòng dataset_versions
        + 1 dòng audit_logs
    end note
```

| Endpoint | Hành động |
|---|---|
| `POST /{dataset_id}/undo` | Chuyển về phiên bản cha |
| `POST /{dataset_id}/redo` | Tiến tới phiên bản sau đã undo |
| `POST /{dataset_id}/restore/{version_id}` | Khôi phục về một phiên bản bất kỳ |

### 4.8 Điểm chất lượng và xuất file

```mermaid
flowchart LR
    V[(Version hiện tại)] --> Q[quality.py<br/>tính các chỉ số]
    Q --> M1[Đầy đủ]
    Q --> M2[Hợp lệ]
    Q --> M3[Duy nhất]
    Q --> M4[Nhất quán]
    M1 & M2 & M3 & M4 --> S[Điểm tổng 0–100<br/>→ quality_reports]
    S --> UI[Plotly: đồng hồ điểm,<br/>biểu đồ missing, phân bố]
    V --> E{Export}
    E -->|GET /{version_id}/csv| C[File CSV sạch]
    E -->|GET /{version_id}/excel| X[File Excel sạch<br/>kèm điểm chất lượng]
```

Chi tiết công thức: [quality_score.md](quality_score.md).

### 4.9 Quản trị (Admin)

```mermaid
flowchart TD
    A([Admin đăng nhập]) --> B{require_admin}
    B -- Không phải admin --> X[403 Forbidden]
    B -- Admin --> C[GET /admin/users<br/>danh sách user]
    C --> D[PATCH /admin/users/id<br/>khóa/mở, đổi role]
    C --> E[POST /admin/users/id/reset-password]
    B --> F[GET /admin/stats<br/>thống kê hệ thống]
    B --> G[GET /audit/all<br/>toàn bộ audit log]
```

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
        PG -.->|host port 5434| H5434[DBeaver / psql]
    end
    BE --> EXT1{{AI API}}
    BE --> EXT2[(Object Storage)]
```

Thứ tự khởi động: `postgres` (healthy) → `backend` (healthy, sau migration) → `frontend`.

### 5.2 Môi trường online (mục tiêu của đề tài)

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

> Nền tảng deploy cụ thể chưa được chọn; sơ đồ 5.2 sẽ cập nhật khi chốt Render/Railway/Fly.io.
