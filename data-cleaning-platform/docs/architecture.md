# Kiến trúc hệ thống

> TODO: hoàn thiện tài liệu này. Dưới đây là dàn ý các mục cần viết.

## 1. Tổng quan

- Mục tiêu hệ thống, bài toán giải quyết.
- Các thành phần chính: Backend (FastAPI), Frontend (Streamlit), PostgreSQL, Storage
  (S3-compatible), AI Provider (OpenAI/Anthropic).

## 2. Sơ đồ kiến trúc tổng thể

- TODO: chèn sơ đồ (user -> frontend -> backend -> DB/Storage/AI).

## 3. Luồng xử lý chính

1. Upload file -> Ingestion -> Profiling -> Detectors.
2. AI sinh gợi ý (rule JSON) -> Validator kiểm tra -> hiển thị cho người dùng.
3. Người dùng xem Preview (dry_run) -> xác nhận -> Rule Engine áp dụng thật -> tạo version mới.
4. Versioning (undo/redo), Audit log, Quality score, Export.

## 4. Nguyên tắc cốt lõi: AI không được exec() code

- Giải thích vì sao AI chỉ được sinh JSON theo DSL (xem [rule_dsl.md](rule_dsl.md)).
- Vai trò của app.schemas.rule (validate cấu trúc) và app.services.ai.validator
  (validate trước khi lưu/thi hành).
- Vai trò duy nhất của Rule Engine (app.services.rules.engine) trong việc sửa dữ liệu thật.

## 5. Cấu trúc thư mục

- TODO: liệt kê và giải thích vai trò từng thư mục chính (core, models, schemas, services,
  api, repositories, workers, data).

## 6. Lựa chọn công nghệ và lý do

- TODO: vì sao chọn FastAPI/SQLAlchemy 2.0/Streamlit/boto3/...

## 7. Khả năng mở rộng

- TODO: hướng mở rộng (worker queue, nhiều AI provider, nhiều loại storage).
