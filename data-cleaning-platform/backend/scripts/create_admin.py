"""Script tạo tài khoản admin đầu tiên cho hệ thống.

Cách dùng:
    python scripts/create_admin.py --email admin@example.com --password Admin123! \
        --full-name "Admin"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.repositories import user_repo  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Tạo tài khoản admin đầu tiên.")
    parser.add_argument("--email", required=True, help="Email đăng nhập của admin.")
    parser.add_argument("--password", required=True, help="Mật khẩu của admin.")
    parser.add_argument("--full-name", default="Administrator", help="Họ tên hiển thị.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = user_repo.get_by_email(db, args.email)
        if existing is not None:
            print(f"Email '{args.email}' đã tồn tại. Không tạo tài khoản mới.")
            return

        user = user_repo.create_user(
            db,
            email=args.email,
            password_hash=hash_password(args.password),
            full_name=args.full_name,
            role="admin",
        )
        print(f"Đã tạo tài khoản admin: id={user.id}, email={user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
