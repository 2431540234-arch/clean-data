"""Truy vấn DB cho bảng projects. Lọc theo owner_id nếu người gọi không phải admin."""

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User


def get_by_id(db: Session, project_id: int) -> Project | None:
    """Lấy project theo id, trả về None nếu không tồn tại."""
    return db.get(Project, project_id)


def list_for_user(db: Session, user: User) -> list[Project]:
    """Lấy danh sách project: admin thấy toàn bộ, user thường chỉ thấy project của mình.

    Gợi ý cách làm: nếu user.role == "admin" -> select(Project); ngược lại
    select(Project).where(Project.owner_id == user.id).
    """
    raise NotImplementedError("TODO: lọc project theo quyền user (admin thấy tất cả).")


def create_project(db: Session, name: str, owner_id: int) -> Project:
    """Tạo project mới thuộc owner_id."""
    raise NotImplementedError("TODO: tạo Project mới, add/commit/refresh.")


def delete_project(db: Session, project: Project) -> None:
    """Xóa project (cascade xóa dataset, version, rule liên quan theo quan hệ model)."""
    raise NotImplementedError("TODO: xóa project khỏi DB.")
