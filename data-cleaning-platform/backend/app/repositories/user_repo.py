"""Truy vấn DB cho bảng users."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: int) -> User | None:
    """Lấy user theo id, trả về None nếu không tồn tại."""
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    """Lấy user theo email, không phân biệt hoa/thường (dùng khi đăng nhập/đăng ký)."""
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return db.execute(stmt).scalars().first()


def create_user(
    db: Session, email: str, password_hash: str, full_name: str, role: str = "user"
) -> User:
    """Tạo user mới và commit vào DB."""
    user = User(email=email, password_hash=password_hash, full_name=full_name, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_all(db: Session) -> list[User]:
    """Lấy toàn bộ user (dùng cho trang quản trị, chỉ admin gọi)."""
    stmt = select(User).order_by(User.created_at.desc())
    return list(db.execute(stmt).scalars().all())
