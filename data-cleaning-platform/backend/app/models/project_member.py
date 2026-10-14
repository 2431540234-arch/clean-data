"""Model ProjectMember: thành viên của project và vai trò (owner/editor/viewer)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


class ProjectMember(Base):
    """Một user tham gia một project với vai trò 'owner' | 'editor' | 'viewer'.

    Hiện bảng chỉ lưu dữ liệu; kiểm quyền truy cập vẫn dựa vào projects.owner_id.
    """

    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_id_user_id"),
        CheckConstraint("role IN ('owner', 'editor', 'viewer')", name="ck_project_members_role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()
