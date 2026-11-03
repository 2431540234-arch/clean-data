"""Truy vấn DB cho bảng audit_logs."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

DEFAULT_LIMIT = 1000
MAX_LIMIT = 5000


def list_for_user(
    db: Session, user_id: int, limit: int = DEFAULT_LIMIT, offset: int = 0
) -> list[AuditLog]:
    """Audit log của riêng một user (mới nhất trước)."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def list_all(db: Session, limit: int = DEFAULT_LIMIT, offset: int = 0) -> list[AuditLog]:
    """Toàn bộ audit log hệ thống (mới nhất trước); chỉ admin gọi."""
    stmt = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))
