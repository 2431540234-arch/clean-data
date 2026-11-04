#!/usr/bin/env bash
# Đưa hệ thống demo về trạng thái sạch: xóa DB và file đã lưu, tạo lại bảng, nạp lại tài khoản demo.
#
# CẢNH BÁO: `docker compose down -v` XÓA VĨNH VIỄN dữ liệu Postgres và thư mục lưu file của compose
# project này (mọi dự án, dataset, phiên bản, nhật ký). Chỉ dùng cho máy demo.
#
# Cách dùng (ở thư mục gốc của repo):  bash scripts/reset-demo.sh   (thêm -y để bỏ qua câu hỏi)
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "${1:-}" != "-y" ]; then
    read -r -p "Việc này XÓA SẠCH dữ liệu demo rồi nạp lại 2 tài khoản mẫu. Gõ RESET để tiếp tục: " answer
    if [ "$answer" != "RESET" ]; then
        echo "Đã hủy, chưa thay đổi gì."
        exit 1
    fi
fi

docker compose down -v
docker compose up -d --build
echo "Chờ backend sẵn sàng..."
for _ in $(seq 1 60); do
    curl -fsS http://localhost:8000/health >/dev/null 2>&1 && break
    sleep 2
done
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/seed.py
echo "Xong. Đăng nhập: user@example.com / User12345, admin@example.com / Admin123!"
