"""Model Project: dự án làm sạch dữ liệu, thuộc về một user (owner_id quyết định quyền truy cập)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.column_mapping import ColumnMapping
    from app.models.dataset import Dataset
    from app.models.project_member import ProjectMember
    from app.models.rule import Rule
    from app.models.user import User


class Project(Base):
    """Dự án do user tạo ra, chứa nhiều dataset, rule template và column mapping."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    datasets: Mapped[list["Dataset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    rules: Mapped[list["Rule"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    column_mappings: Mapped[list["ColumnMapping"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
