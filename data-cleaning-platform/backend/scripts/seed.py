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
from app.repositories import dataset_repo, project_repo, user_repo  # noqa: E402
from app.services import dataset_service  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
DEMO_PROJECT = "Khách hàng 2026"
DEMO_FILE = "khach_hang_ban.csv"

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
        _seed_demo_dataset(db)
    finally:
        db.close()
    return 0


def _seed_demo_dataset(db) -> None:
    """Tạo dự án demo của user thường và tải lên file mẫu (nếu có và chưa có dataset)."""
    owner = user_repo.get_by_email(db, DEMO_USERS[1][0])
    sample = SAMPLE_DIR / DEMO_FILE
    if owner is None or not sample.exists():
        return
    project = next(
        (p for p in project_repo.list_for_user(db, owner) if p.name == DEMO_PROJECT), None
    )
    if project is None:
        project = project_repo.create_project(db, DEMO_PROJECT, owner.id)
        print(f"Đã tạo dự án: {project.name} (id={project.id})")
    if dataset_repo.list_datasets_for_project(db, project.id):
        print(f"Dự án '{project.name}' đã có dataset (bỏ qua)")
        return
    outcome = dataset_service.create_dataset_from_file(
        db, owner, project, DEMO_FILE, sample.read_bytes()
    )
    print(f"Đã tải dataset mẫu: {outcome.dataset.name} (id={outcome.dataset.id})")


if __name__ == "__main__":
    sys.exit(main())
