"""Ghi audit log cho các hành động quan trọng: upload, apply rule, undo, redo, export."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int,
    action: str,
    dataset_id: int | None = None,
    before_version: int | None = None,
    after_version: int | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    """Tạo một dòng audit log mới và commit vào DB.

    Args:
        user_id: người thực hiện hành động.
        action: mã hành động, ví dụ "dataset.upload", "version.apply_rule", "user.lock".
        dataset_id: dataset liên quan (None nếu là hành động quản trị không gắn dataset).
        before_version / after_version: version_no trước/sau hành động (nếu có).
        detail: thông tin bổ sung dạng JSON, ví dụ rule_json đã áp dụng.
    """
    entry = AuditLog(
        user_id=user_id,
        dataset_id=dataset_id,
        action=action,
        before_version=before_version,
        after_version=after_version,
        detail=detail or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
