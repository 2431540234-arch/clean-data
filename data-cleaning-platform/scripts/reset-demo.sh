#!/usr/bin/env bash
# Đưa dữ liệu demo về trạng thái sạch, KHÔNG build lại image, KHÔNG đụng frontend.
#
# Việc script làm (chỉ trong compose project của repo này):
#   1. Dừng container backend (không xóa).
#   2. Trong container Postgres, database data_cleaning:  DROP SCHEMA public CASCADE; CREATE SCHEMA public;
#      -> xóa mọi bảng và dữ liệu (người dùng, dự án, dataset, phiên bản, nhật ký). Không xóa volume Postgres.
#   3. Xóa NỘI DUNG volume lưu file dataset (dcp_storage, gắn vào /app/data/storage của backend).
#      Không xóa volume nào khác và không xóa chính volume.
#   4. Bật lại backend, chạy `alembic upgrade head`, rồi `scripts/seed.py` (2 tài khoản demo + dự án mẫu).
#
# Tùy chọn --host-storage (chỉ khi backend chạy NGOÀI Docker): xóa nội dung backend/data/storage trên máy,
# có câu xác nhận riêng (gõ XOA-FILE). Chỉ động tới đúng thư mục đó trong repo.
#
# Cách dùng:
#   bash scripts/reset-demo.sh                 # hỏi xác nhận RESET
#   bash scripts/reset-demo.sh -y              # bỏ qua câu hỏi RESET (KHÔNG bỏ qua câu hỏi XOA-FILE)
#   bash scripts/reset-demo.sh --host-storage  # thêm dọn backend/data/storage
#   bash scripts/reset-demo.sh -p dcp-test -f docker-compose.dcp-test.yml   # chạy trên project khác
#   (--host-storage-yes bỏ qua câu hỏi XOA-FILE, chỉ dùng trong script tự động)
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

YES=0 HOST_STORAGE=0 HOST_STORAGE_YES=0 COMPOSE=(docker compose)
while [ $# -gt 0 ]; do
    case "$1" in
        -y) YES=1 ;;
        --host-storage) HOST_STORAGE=1 ;;
        --host-storage-yes) HOST_STORAGE_YES=1 ;;
        -f) COMPOSE+=(-f "$2"); shift ;;
        -p) COMPOSE+=(-p "$2"); shift ;;
        *) echo "Tùy chọn không hợp lệ: $1" >&2; exit 2 ;;
    esac
    shift
done

if [ "$YES" -ne 1 ]; then
    read -r -p "Việc này XÓA SẠCH dữ liệu demo (DB data_cleaning và file dataset) rồi nạp lại 2 tài khoản mẫu. Gõ RESET để tiếp tục: " answer
    if [ "$answer" != "RESET" ]; then
        echo "Đã hủy, chưa thay đổi gì."
        exit 1
    fi
fi

if [ "$HOST_STORAGE" -eq 1 ] && [ "$HOST_STORAGE_YES" -ne 1 ]; then
    read -r -p "Cũng XÓA NỘI DUNG thư mục backend/data/storage trên máy này? Gõ XOA-FILE để đồng ý: " host_answer
    if [ "$host_answer" != "XOA-FILE" ]; then
        echo "Đã hủy, chưa thay đổi gì."
        exit 1
    fi
fi

echo "1/4 Dừng backend..."
"${COMPOSE[@]}" stop backend

echo "2/4 Xóa schema public trong database data_cleaning (Postgres trong Docker)..."
"${COMPOSE[@]}" exec -T postgres psql -U postgres -d data_cleaning -v ON_ERROR_STOP=1 \
    -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

echo "3/4 Xóa nội dung volume lưu file dataset (/app/data/storage)..."
"${COMPOSE[@]}" run --rm --no-deps --entrypoint sh backend \
    -c "find /app/data/storage -mindepth 1 -delete"

if [ "$HOST_STORAGE" -eq 1 ]; then
    HOST_DIR="$PROJECT_ROOT/backend/data/storage"
    if [ -d "$HOST_DIR" ]; then
        echo "     Dọn nội dung $HOST_DIR"
        find "$HOST_DIR" -mindepth 1 -delete
    else
        echo "     Không có thư mục backend/data/storage, bỏ qua."
    fi
fi

echo "4/4 Bật lại backend, chạy migration và nạp tài khoản demo..."
"${COMPOSE[@]}" up -d backend
for _ in $(seq 1 60); do
    "${COMPOSE[@]}" exec -T backend python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" >/dev/null 2>&1 && break
    sleep 2
done
"${COMPOSE[@]}" exec -T backend alembic upgrade head
"${COMPOSE[@]}" exec -T backend python scripts/seed.py
echo "Xong. Đăng nhập: user@example.com / User12345, admin@example.com / Admin123!"
