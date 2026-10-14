"""Model ColumnMapping: ánh xạ tên cột nguồn sang tên cột chuẩn trong một project."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class ColumnMapping(Base):
    """source_name (tên cột trong file) -> standard_name (tên chuẩn); confirmed khi user duyệt."""

    __tablename__ = "column_mappings"
    __table_args__ = (
        UniqueConstraint("project_id", "source_name", name="uq_column_mappings_project_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    standard_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="column_mappings")
