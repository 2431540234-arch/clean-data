.PHONY: dev test lint format migrate create-admin seed-demo

# Chạy toàn bộ hệ thống bằng Docker Compose
dev:
	docker compose up --build

# Chạy test backend
test:
	cd backend && pytest

# Kiểm tra lint bằng ruff
lint:
	cd backend && ruff check .

# Format code bằng black + ruff
format:
	cd backend && black . && ruff check --fix .

# Chạy migration Alembic lên bản mới nhất
migrate:
	cd backend && alembic upgrade head

# Tạo tài khoản admin đầu tiên
create-admin:
	cd backend && python scripts/create_admin.py

# Nạp dữ liệu demo
seed-demo:
	cd backend && python scripts/seed_demo.py
