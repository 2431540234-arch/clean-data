# Data Cleaning Platform

Nền tảng web làm sạch dữ liệu Excel/CSV có AI gợi ý chuẩn hóa. Người dùng upload file,
hệ thống phân tích schema, phát hiện lỗi (trùng lặp, thiếu dữ liệu, outlier, sai định dạng
ngày/số điện thoại/email), gợi ý rule làm sạch dạng JSON, người dùng xem preview
trước/sau rồi mới xác nhận áp dụng. Hệ thống có versioning (undo/redo), audit log,
điểm chất lượng dữ liệu (data quality score), và xuất CSV/Excel.

> **Nguyên tắc cốt lõi:** AI chỉ sinh **rule JSON**, **KHÔNG BAO GIỜ** sinh code để `exec()`.
> Chỉ **Rule Engine** (Pandas) mới được phép sửa dữ liệu thật.

## Kiến trúc tổng quan

- **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 + Alembic
- **Frontend:** Streamlit + Plotly (chỉ giao diện sáng, tiếng Việt)
- **AI (tùy chọn):** Anthropic (mặc định) hoặc OpenAI, chỉ sinh JSON rule và có validator kiểm tra.
  Không có khóa API thì hệ thống vẫn chạy đầy đủ bằng gợi ý theo quy tắc.
- **Lưu trữ file:** thư mục trên máy (mặc định, `backend/data/storage`) hoặc S3-compatible
  (Supabase Storage / Cloudflare R2) khi đặt `STORAGE_ENDPOINT` và khóa
- **Auth:** JWT, 2 quyền `admin` và `user`

Chi tiết xem [docs/architecture.md](docs/architecture.md) và
[docs/flow-diagram.md](docs/flow-diagram.md).

## Chạy toàn bộ hệ thống trên máy mới

Cần: **Git**, **Python 3.11**, **Docker Desktop** (chỉ để chạy PostgreSQL). Các lệnh dưới đây chạy từ
thư mục `data-cleaning-platform/`. Trên Windows dùng PowerShell; chỗ khác biệt được ghi chú.

### Bước 1. Lấy mã và tạo file môi trường

```bash
git clone <địa-chỉ-repo> && cd <repo>/data-cleaning-platform
cp .env.example .env            # Windows: Copy-Item .env.example .env
```

Mở `.env` và kiểm tra: `DATABASE_URL` (cổng phải khớp `POSTGRES_PORT`), `JWT_SECRET` (đổi thành chuỗi
ngẫu nhiên nếu không phải máy thử). Các khóa AI để trống nếu chưa có.

### Bước 2. Chạy PostgreSQL bằng Docker

```bash
docker compose up -d postgres   # chạy Postgres 16, tự tạo DB data_cleaning
docker compose ps               # chờ trạng thái "healthy"
```

### Bước 3. Cài backend, tạo bảng (migration) và nạp tài khoản demo

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate        Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
alembic upgrade head            # tạo 16 bảng
python scripts/seed.py          # 2 tài khoản demo + dự án "Khách hàng 2026" có sẵn 1 dataset mẫu
```

`seed.py` chỉ chạy thủ công và từ chối chạy khi `ENVIRONMENT=production`. Tài khoản demo:

| Vai trò | Email | Mật khẩu |
|---|---|---|
| Người dùng | `user@example.com` | `User12345` |
| Quản trị viên | `admin@example.com` | `Admin123!` |

### Bước 4. Chạy backend (terminal 1)

```bash
cd backend
uvicorn app.main:app --reload   # API: http://localhost:8000, Swagger: http://localhost:8000/docs
curl http://localhost:8000/health   # => {"status":"ok"}
```

### Bước 5. Chạy frontend (terminal 2)

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py            # http://localhost:8501
```

Frontend gọi backend ở `http://localhost:8000` (đổi bằng biến môi trường `BACKEND_URL`). **Không** đặt
`FRONTEND_MOCK` để dùng backend thật; đặt `FRONTEND_MOCK=1` nếu chỉ muốn xem giao diện bằng dữ liệu mẫu,
không cần backend (xem [frontend/README.md](frontend/README.md)).

### Cách khác: chạy cả ba dịch vụ bằng Docker Compose

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
```

Frontend <http://localhost:8501>, backend <http://localhost:8000/docs>.

Bản giao diện mới nhận ra bằng: menu ngang có đủ **Trang chủ · Dự án · Làm sạch dữ liệu · Thư viện quy tắc · Nhật ký · Tài khoản** (thêm **Quản trị** với admin), và thanh 6 bước chỉ hiện ở các trang của quy trình làm sạch.

### Cách chạy chuẩn cho ngày bảo vệ

**Cách chính (A): chạy cả ba dịch vụ bằng Docker, build lại sau khi chốt code.**

```bash
docker compose up -d --build        # postgres + backend + frontend, dữ liệu nằm trong 2 volume
# lần đầu hoặc sau reset: docker compose exec backend python scripts/seed.py
```

Mở <http://localhost:8501>. Mỗi lần sửa code giao diện phải build lại (`docker compose up -d --build frontend`),
nếu không cổng 8501 vẫn là bản cũ. Kiểm tra bằng cách đăng nhập và xem menu có mục **Thư viện quy tắc**.

**Cách dự phòng (B): chạy Streamlit trực tiếp** (sửa nhanh phút chót, không cần build). Phải giải phóng cổng 8501 trước:

```bash
docker compose stop frontend        # bắt buộc, nếu không Streamlit báo cổng 8501 đã bị chiếm
cd frontend && streamlit run app.py
```

Khi đang dùng cách B, đừng chạy `docker compose up` không kèm tên dịch vụ (nó bật lại container frontend và chiếm cổng 8501).

### Dữ liệu được lưu ở đâu

| Dữ liệu | Chạy bằng Docker Compose | Backend chạy ngoài Docker |
|---|---|---|
| Bản ghi (người dùng, dự án, dataset, phiên bản, nhật ký) | Volume `dcp_postgres_data` (Postgres) | Postgres của bạn (`DATABASE_URL`) |
| File dataset (Parquet) | Volume `dcp_storage`, gắn vào `/app/data/storage` trong container backend | Thư mục `backend/data/storage` trên máy |

Hai nơi này phải đi cùng nhau: DB giữ bản ghi, thư mục lưu trữ giữ nội dung file. Nhờ hai volume,
`docker compose up -d --build backend` (tạo lại container) không làm mất dữ liệu. Chỉ `docker compose down -v`
mới xóa cả hai volume. Nếu dùng S3 (đặt `STORAGE_ENDPOINT` thật) thì file nằm ở bucket, không ở `dcp_storage`.
Muốn làm sạch dữ liệu demo, dùng script reset ở mục "Reset trước ngày bảo vệ" thay vì xóa tay một trong hai nơi.

### Kiểm thử

```bash
pip install -r backend/requirements-dev.txt       # pytest, ruff, black (một lần)
cd backend && pytest            # cần Postgres đang chạy; tự tạo DB data_cleaning_test và data_cleaning_migration
cd frontend && pytest           # không cần backend (dùng dữ liệu mẫu); cần pytest đã cài ở trên
```

## Kịch bản demo (nên mở file nào ở bước nào)

Đăng nhập bằng `user@example.com` / `User12345`. File mẫu nằm trong [sample_data/](sample_data/).

| Bước | Trang | Việc làm | File |
|---|---|---|---|
| 1 | Dự án | Tạo dự án "Demo gợi ý làm sạch" (dự án mới tự thành dự án đang chọn) | — |
| 2 | Tải lên | Tải file, xem thông tin file và 20 dòng đầu | **`khach_hang_ban.csv`** |
| 3 | Tổng quan dữ liệu | Xem điểm chất lượng (≈ 90,5) và 4 tiêu chí thành phần, thống kê cột, tab **Lỗi đã phát hiện** (13 nhóm lỗi), biểu đồ | `khach_hang_ban.csv` |
| 4 | Làm sạch dữ liệu | **Sinh gợi ý** (10 gợi ý), **Chấp nhận tất cả chưa duyệt** → **Xem trước** → **Áp dụng thay đổi** | `khach_hang_ban.csv` |
| 5 | Lịch sử phiên bản | Xem chi tiết từng phiên bản, thử **Hoàn tác** và **Làm lại** | — |
| 6 | Tổng quan dữ liệu | Điểm chất lượng tăng (≈ 98,4), số dòng còn 29, thêm 1 cột | — |
| 7 | Xuất dữ liệu | Tải CSV và Excel (3 sheet: Dữ liệu, Báo cáo chất lượng, Lỗi đã phát hiện) | — |
| 8 | Tải lên → Mapping cột | Tải file có **tiêu đề tiếng Việt khác chuẩn**, bấm *Điền ví dụ* → *Gợi ý mapping* → *Xác nhận và sang bước 4* (6/7 cột khớp) | **`khach_hang_tieu_de_khac.csv`** |
| 9 | Tài khoản | Đổi mật khẩu: vẫn ở lại trang, hiện thông báo thành công | — |
| 10 | Đăng nhập admin (`admin@example.com`) | Quản trị người dùng, Thống kê hệ thống, Nhật ký (bật *Xem toàn hệ thống*) | — |

Ghi chú: `khach_hang_ban.csv` (và `nhan_su_ban.xlsx`, cùng cấu trúc, có nhiều sheet) được cài sẵn các lỗi
để minh họa gợi ý làm sạch, xem [sample_data/README.md](sample_data/README.md). `khach_hang_tieu_de_khac.csv`
khá sạch nên **chỉ dùng cho phần Mapping cột**: nó gần như không sinh gợi ý làm sạch. Ảnh chụp từng bước nằm
ở [docs/screenshots/real-backend/](docs/screenshots/real-backend/README.md).

## Checklist ngày bảo vệ

Làm theo thứ tự, tick từng mục:

1. [ ] **Đóng băng code**: `git status` sạch, đang ở `main` (tag `v1.0-bao-ve`), không sửa thêm gì.
2. [ ] **Reset dữ liệu**: `powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1` (gõ `RESET`). Xem mục "Reset trước ngày bảo vệ".
3. [ ] **Build container**: `docker compose up -d --build`, chờ `docker compose ps` báo cả ba dịch vụ `healthy`.
4. [ ] **Kiểm tra bản mới ở <http://localhost:8501>**: đăng nhập `user@example.com` / `User12345`, menu có mục **Thư viện quy tắc**; `curl http://localhost:8000/health` trả `{"status":"ok"}`.
5. [ ] **Đi thử kịch bản demo một lượt** (mục "Kịch bản demo"), xong thì reset lại ở bước 2 để máy sạch trước giờ trình bày.

Sự cố giữa chừng: xem "Xử lý sự cố"; cần sửa nhanh thì dùng cách dự phòng B (`docker compose stop frontend` rồi `streamlit run app.py`).

## Reset trước ngày bảo vệ

Đưa máy demo về trạng thái sạch: xóa mọi dự án, dataset, phiên bản, nhật ký; nạp lại 2 tài khoản mẫu. **Lệnh này xóa vĩnh viễn dữ liệu demo**, hãy tự chạy khi đã chắc chắn:

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1
# Linux/macOS
bash scripts/reset-demo.sh
```

Script chỉ làm bốn việc, không build lại image và không đụng container frontend:

1. Dừng container backend (không xóa).
2. Trong container Postgres, database `data_cleaning`: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` (không xóa volume `dcp_postgres_data`).
3. Xóa **nội dung** volume `dcp_storage` (file dataset), không xóa volume nào khác.
4. Bật lại backend, chạy `alembic upgrade head` rồi `scripts/seed.py`.

Phải gõ `RESET` để tiếp tục (thêm `-Yes` hoặc `-y` để bỏ qua câu hỏi này).

Nếu backend chạy **ngoài Docker** (file nằm ở `backend/data/storage` trên máy), thêm `-HostStorage` (`--host-storage` với bash) để script dọn luôn nội dung thư mục đó. Việc này có câu xác nhận riêng (gõ `XOA-FILE`) và `-Yes` không bỏ qua được câu đó. Script chỉ động tới đúng thư mục `backend/data/storage` trong repo.

Chạy trên một compose project khác (ví dụ để thử): `-Project dcp-test -ComposeFile <file compose>` (`-p`, `-f` với bash).

## Xử lý sự cố

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Frontend báo "Không kết nối được tới máy chủ" | Backend chưa chạy, hoặc chạy ở cổng khác | Chạy `curl http://localhost:8000/health`. Nếu cổng khác, đặt `BACKEND_URL` rồi chạy lại frontend |
| `uvicorn` báo cổng 8000 đã bị chiếm, hoặc frontend nói chuyện nhầm với một tiến trình cũ | Một server cũ còn chạy | Windows: `netstat -ano \| findstr :8000` rồi `taskkill /PID <pid> /F`. Hoặc chạy cổng khác: `uvicorn app.main:app --port 8010` và `BACKEND_URL=http://localhost:8010` cho frontend |
| `docker compose up` báo "cannot connect to the Docker daemon" / `alembic` báo không kết nối được DB | Docker Desktop chưa chạy, hoặc Postgres chưa healthy | Mở Docker Desktop, chờ biểu tượng xanh, `docker compose up -d postgres`, `docker compose ps` đến khi `healthy` |
| Postgres không khởi động vì cổng 5432 bị chiếm | Máy đã có Postgres khác | Đặt `POSTGRES_PORT=5434` trong `.env` và sửa cổng trong `DATABASE_URL`, rồi `docker compose up -d postgres` |
| `alembic` báo "Can't locate revision 0002" | DB cũ tạo từ chuỗi migration trước khi gộp | `UPDATE alembic_version SET version_num = '0001';` rồi `alembic upgrade head`, hoặc xóa DB tạo lại (`docker compose down -v`) |
| Đăng nhập báo "quá nhiều lần" (429) | Sai mật khẩu 5 lần trong 15 phút | Chờ 15 phút. Trên máy demo có thể xóa các dòng `auth.login_failed` trong bảng `audit_logs` |
| Không thấy gợi ý của AI (nguồn luôn là "Quy tắc") | Chưa có `ANTHROPIC_API_KEY` | Đây là hành vi đúng: hệ thống chạy bằng quy tắc. Muốn dùng AI, điền khóa vào `.env` (không commit) và khởi động lại backend; đổi mô hình bằng `AI_MODEL` |
| Gọi AI chậm hoặc lỗi | Mạng/khóa/hạn mức | Hệ thống tự dùng gợi ý theo quy tắc sau tối đa `AI_TIMEOUT_SECONDS` giây; lỗi được ghi vào bảng `ai_requests` (không ghi dữ liệu hay khóa) |
| Tải file lên bị từ chối | Quá `MAX_UPLOAD_MB` (413), sai định dạng, hoặc quá `MAX_UPLOAD_ROWS`/`MAX_UPLOAD_COLUMNS` | Dùng CSV/XLSX/XLS hợp lệ, thu nhỏ file hoặc tăng giới hạn trong `.env` |
| Windows báo lỗi chữ tiếng Việt khi chạy script | Console dùng bảng mã cp1252 | Đặt `PYTHONUTF8=1` trước khi chạy script |
| Mở http://localhost:8501 thấy giao diện cũ (menu không có mục **Thư viện quy tắc**, không có hàng menu ngang dưới thanh logo) | Container `dcp_frontend` dựng từ image cũ; `docker compose up -d` không tự build lại | Kiểm tra: `docker image ls data-cleaning-platform-frontend` (cột CREATED phải là thời điểm gần đây). Dùng bản mới bằng `docker compose up -d --build frontend` (cách chính); dự phòng: `docker compose stop frontend` rồi chạy `streamlit run app.py` ở Bước 5 |
| Muốn xóa sạch dữ liệu demo | — | Chạy script reset bên dưới (mục "Reset trước ngày bảo vệ") |

## Lệnh tắt (Makefile)

| Lệnh                | Ý nghĩa                              |
|---------------------|----------------------------------------|
| `make dev`           | Chạy toàn bộ hệ thống qua Docker Compose |
| `make test`          | Chạy pytest cho backend                |
| `make lint`          | Kiểm tra lint bằng ruff                |
| `make format`        | Format code bằng black + ruff          |
| `make migrate`       | Chạy migration Alembic                 |
| `make create-admin`  | Tạo tài khoản admin đầu tiên           |
| `make seed-demo`     | Nạp tài khoản và dataset demo (`scripts/seed.py`) |

## Cấu trúc thư mục

Xem chi tiết toàn bộ cây thư mục và vai trò từng module trong
[docs/architecture.md](docs/architecture.md).

## Tài liệu

- [docs/architecture.md](docs/architecture.md) — Kiến trúc hệ thống
- [docs/api.md](docs/api.md) — Danh sách API
- [docs/permissions.md](docs/permissions.md) — Ma trận quyền admin/user
- [docs/rule_dsl.md](docs/rule_dsl.md) — Đặc tả DSL rule làm sạch
- [docs/quality_score.md](docs/quality_score.md) — Công thức tính điểm chất lượng
- [docs/BACKEND_NOTES.md](docs/BACKEND_NOTES.md) — Ghi chú thiết kế từng nhóm backend (để bảo vệ đồ án)
- [docs/BACKEND_TODO.md](docs/BACKEND_TODO.md) — Hợp đồng frontend–backend và trạng thái cài đặt
- [docs/deployment.md](docs/deployment.md) — Hướng dẫn triển khai
- [docs/user_guide.md](docs/user_guide.md) — Hướng dẫn sử dụng

## Demo

URL demo: _TODO: điền URL sau khi deploy._
