"""Quy tắc phân quyền truy cập tài nguyên: admin thấy tất cả, user chỉ thấy của mình."""

from app.core.exceptions import ForbiddenError
from app.models.project import Project
from app.models.user import User


def can_access_project(user: User, project: Project) -> bool:
    """Trả về True nếu user là admin hoặc là chủ sở hữu (owner) của project."""
    return user.role == "admin" or project.owner_id == user.id


def ensure_can_access_project(user: User, project: Project) -> None:
    """Giống ``can_access_project`` nhưng raise ForbiddenError nếu không được phép.

    Dùng trong các router cần chặn truy cập chéo dữ liệu giữa user A và user B.
    """
    if not can_access_project(user, project):
        raise ForbiddenError("Bạn không có quyền truy cập dự án này.")
