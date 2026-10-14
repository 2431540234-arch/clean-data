"""Model AuditLog: ghi lại mọi hành động quan trọng (upload, apply rule, undo, redo, export...)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class AuditLog(Base):
    """Một dòng audit log, chỉ ghi thêm (không xóa theo cascade).

    Khi user/project bị xóa thì user_id/project_id chuyển về NULL, dòng log vẫn được giữ.
    entity_type/entity_id: đối tượng bị tác động (ví dụ 'dataset', 'user'); old_value/new_value:
    trạng thái trước/sau (ví dụ {"version_number": 2}).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_project_id_created_at", "project_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    entity_id: Mapped[int | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User | None"] = relationship()
    project: Mapped["Project | None"] = relationship()
