"""Nạp tài khoản demo vào DB (giống chế độ dữ liệu mẫu của frontend).

Chỉ chạy khi gọi thủ công, KHÔNG được gắn vào lệnh khởi động nào và từ chối chạy ở production.

Cách dùng (từ thư mục backend/):
    python scripts/seed.py
"""

import sys
from pathlib import Path

# Console Windows mặc định không in được tiếng Việt (cp1252): ép UTF-8.
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.repositories import user_repo  # noqa: E402

DEMO_USERS = [
    ("admin@example.com", "Admin123!", "Trần Quốc Bảo", "admin"),
    ("user@example.com", "User12345", "Nguyễn Thị Minh Anh", "user"),
]


def main() -> int:
    """Tạo các tài khoản demo chưa tồn tại; trả mã thoát của tiến trình."""
    if settings.ENVIRONMENT.lower() == "production":
        print("Từ chối: không nạp tài khoản demo ở môi trường production.")
        return 1

    db = SessionLocal()
    try:
        for email, password, full_name, role in DEMO_USERS:
            if user_repo.get_by_email(db, email) is not None:
                print(f"Đã có: {email} (bỏ qua)")
                continue
            user = user_repo.create_user(
                db,
                email=email,
                password_hash=hash_password(password),
                full_name=full_name,
                role=role,
            )
            print(f"Đã tạo {role}: {user.email} (id={user.id})")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
