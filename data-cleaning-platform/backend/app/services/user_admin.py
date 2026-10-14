"""Nghiệp vụ quản trị tài khoản: khóa/mở, đổi quyền, reset mật khẩu (chỉ admin gọi)."""

from sqlalchemy.orm import Session

from app.models.user import User


def set_user_active(db: Session, target_user_id: int, is_active: bool) -> User:
    """Khóa hoặc mở khóa một tài khoản user.

    Gợi ý cách làm: lấy user bằng app.repositories.user_repo, set is_active, commit,
    ghi audit log qua app.services.audit.log_action.
    """
    raise NotImplementedError("TODO: khóa/mở tài khoản và ghi audit log.")


def change_user_role(db: Session, target_user_id: int, new_role: str) -> User:
    """Đổi quyền (role) của một user giữa 'admin' và 'user'."""
    raise NotImplementedError("TODO: đổi role user, validate new_role hợp lệ, ghi audit log.")


def reset_user_password(db: Session, target_user_id: int, new_password: str) -> None:
    """Admin đặt lại mật khẩu cho một user (quên mật khẩu)."""
    raise NotImplementedError(
        "TODO: hash mật khẩu mới bằng app.core.security.hash_password và lưu, ghi audit log."
    )
