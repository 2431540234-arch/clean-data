"""Nghiệp vụ quản trị tài khoản: khóa/mở, đổi quyền, reset mật khẩu (chỉ admin gọi)."""

import secrets
import string
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.security import hash_password
from app.models.user import User
from app.services.audit import log_action

VALID_ROLES = ("admin", "user")
TEMP_PASSWORD_LENGTH = 12
_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _get_locked(db: Session, user_id: int) -> User:
    user = db.get(User, user_id, with_for_update=True)
    if user is None:
        raise NotFoundError("Không tìm thấy người dùng.")
    return user


def _other_active_admins(db: Session, user_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin", User.is_active.is_(True), User.id != user_id)
        )
        or 0
    )


def _ensure_not_last_admin(db: Session, user: User, action: str) -> None:
    """Không cho hạ quyền/khóa quản trị viên đang hoạt động cuối cùng (hệ thống mất admin)."""
    if user.role == "admin" and user.is_active and _other_active_admins(db, user.id) == 0:
        db.rollback()
        raise ConflictError(f"Không thể {action} quản trị viên đang hoạt động cuối cùng.")


def set_user_active(
    db: Session,
    admin_id: int,
    target_user_id: int,
    is_active: bool,
    ip_address: str | None = None,
    commit: bool = True,
) -> User:
    """Khóa hoặc mở khóa một tài khoản; token cũ của tài khoản bị khóa bị từ chối ngay."""
    user = _get_locked(db, target_user_id)
    if user.is_active != is_active:
        if not is_active:
            _ensure_not_last_admin(db, user, "khóa")
        user.is_active = is_active
        log_action(
            db,
            admin_id,
            "user.unlock" if is_active else "user.lock",
            "user",
            user.id,
            old_value={"is_active": not is_active},
            new_value={"is_active": is_active},
            ip_address=ip_address,
            commit=False,
        )
    if commit:
        db.commit()
        db.refresh(user)
    return user


def change_user_role(
    db: Session,
    admin_id: int,
    target_user_id: int,
    new_role: str,
    ip_address: str | None = None,
    commit: bool = True,
) -> User:
    """Đổi quyền (role) của một user giữa 'admin' và 'user'."""
    if new_role not in VALID_ROLES:
        raise ValidationAppError("Quyền phải là 'admin' hoặc 'user'.")
    user = _get_locked(db, target_user_id)
    if user.role != new_role:
        if new_role != "admin":
            _ensure_not_last_admin(db, user, "hạ quyền")
        old_role, user.role = user.role, new_role
        log_action(
            db,
            admin_id,
            "user.change_role",
            "user",
            user.id,
            old_value={"role": old_role},
            new_value={"role": new_role},
            ip_address=ip_address,
            commit=False,
        )
    if commit:
        db.commit()
        db.refresh(user)
    return user


def reset_user_password(
    db: Session, admin_id: int, target_user_id: int, ip_address: str | None = None
) -> str:
    """Đặt lại mật khẩu thành một mật khẩu tạm ngẫu nhiên và trả về (chỉ hiển thị một lần).

    Mọi token cũ của user bị vô hiệu. Mật khẩu tạm không được ghi vào nhật ký hay log.
    """
    user = _get_locked(db, target_user_id)
    new_password = "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(TEMP_PASSWORD_LENGTH))
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    log_action(
        db,
        admin_id,
        "user.reset_password",
        "user",
        user.id,
        ip_address=ip_address,
        commit=False,
    )
    db.commit()
    return new_password
