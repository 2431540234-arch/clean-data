"""Ghi audit log cho các hành động quan trọng: upload, apply rule, undo, redo, export."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    project_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Tạo một dòng audit log mới và commit vào DB.

    Args:
        user_id: người thực hiện hành động (None nếu hệ thống tự thực hiện).
        action: mã hành động, ví dụ "dataset.upload", "version.apply_rule", "user.lock".
        entity_type: loại đối tượng bị tác động, ví dụ "dataset", "project", "user", "system".
        entity_id: id của đối tượng đó (None nếu không gắn đối tượng cụ thể).
        project_id: project liên quan (nếu có).
        old_value / new_value: trạng thái trước/sau, ví dụ {"version_number": 1} và
            {"version_number": 2, "rule": {...}}.
        ip_address: địa chỉ IP của request (nếu có).
    """
    entry = AuditLog(
        user_id=user_id,
        project_id=project_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
