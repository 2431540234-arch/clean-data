"""Truy vấn DB cho bảng audit_logs."""

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def list_for_user(db: Session, user_id: int) -> list[AuditLog]:
    """Lấy audit log của riêng một user (dùng cho trang 'log của mình')."""
    raise NotImplementedError(
        "TODO: select AuditLog where user_id = user_id, order by created_at desc."
    )


def list_all(db: Session) -> list[AuditLog]:
    """Lấy toàn bộ audit log hệ thống (chỉ admin gọi)."""
    raise NotImplementedError("TODO: select toàn bộ AuditLog, order by created_at desc.")
