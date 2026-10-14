# Data Cleaning Platform

Nền tảng web làm sạch dữ liệu Excel/CSV có AI gợi ý chuẩn hóa. Người dùng upload file,
hệ thống phân tích schema, phát hiện lỗi (trùng lặp, thiếu dữ liệu, outlier, sai định dạng
ngày/số điện thoại/email), AI gợi ý rule làm sạch dạng JSON, người dùng xem preview
trước/sau rồi mới xác nhận áp dụng. Hệ thống có versioning (undo/redo), audit log,
điểm chất lượng dữ liệu (data quality score), và xuất CSV/Excel.

> **Nguyên tắc cốt lõi:** AI chỉ sinh **rule JSON**, **KHÔNG BAO GIỜ** sinh code để `exec()`.
> Chỉ **Rule Engine** (Pandas) mới được phép sửa dữ liệu thật.

## Kiến trúc tổng quan

- **Backend:** FastAPI + SQLAlchemy 2.0 + PostgreSQL + Alembic
- **Frontend:** Streamlit + Plotly
- **AI:** OpenAI / Anthropic (chỉ sinh JSON rule, có validator kiểm tra)
- **Lưu trữ file:** S3-compatible (Supabase Storage / Cloudflare R2) qua boto3
- **Auth:** JWT, 2 quyền `admin` và `user`

Chi tiết xem [docs/architecture.md](docs/architecture.md).

## Cài đặt & chạy bằng Docker Compose (khuyến nghị)

1. Sao chép file môi trường mẫu và điền giá trị thật:

   ```bash
   cp .env.example .env
   ```

2. Khởi động toàn bộ hệ thống (Postgres + Backend + Frontend):

   ```bash
   docker compose up -d --build
   ```

3. Kiểm tra backend đã chạy:

   ```bash
   curl http://localhost:8000/health
   # => {"status": "ok"}
   ```

4. Tạo tài khoản admin đầu tiên:

   ```bash
   docker compose exec backend python scripts/create_admin.py --email admin@example.com --password Admin123!
   ```

5. Mở frontend tại <http://localhost:8501>, backend docs (Swagger) tại
   <http://localhost:8000/docs>.

## Chạy không dùng Docker (local dev)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/create_admin.py --email admin@example.com --password Admin123!
uvicorn app.main:app --reload

# Frontend (terminal khác)
cd frontend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Lệnh tắt (Makefile)

| Lệnh                | Ý nghĩa                              |
|---------------------|----------------------------------------|
| `make dev`           | Chạy toàn bộ hệ thống qua Docker Compose |
| `make test`          | Chạy pytest cho backend                |
| `make lint`          | Kiểm tra lint bằng ruff                |
| `make format`        | Format code bằng black + ruff          |
| `make migrate`       | Chạy migration Alembic                 |
| `make create-admin`  | Tạo tài khoản admin đầu tiên           |
| `make seed-demo`     | Nạp dữ liệu demo                       |

## Cấu trúc thư mục

Xem chi tiết toàn bộ cây thư mục và vai trò từng module trong
[docs/architecture.md](docs/architecture.md).

## Tài liệu

- [docs/architecture.md](docs/architecture.md) — Kiến trúc hệ thống
- [docs/api.md](docs/api.md) — Danh sách API
- [docs/permissions.md](docs/permissions.md) — Ma trận quyền admin/user
- [docs/rule_dsl.md](docs/rule_dsl.md) — Đặc tả DSL rule làm sạch
- [docs/quality_score.md](docs/quality_score.md) — Công thức tính điểm chất lượng
- [docs/deployment.md](docs/deployment.md) — Hướng dẫn triển khai
- [docs/user_guide.md](docs/user_guide.md) — Hướng dẫn sử dụng

## Demo

URL demo: _TODO: điền URL sau khi deploy._
