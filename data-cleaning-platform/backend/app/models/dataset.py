"""Model Dataset và DatasetVersion: file dữ liệu upload và các phiên bản sau khi làm sạch."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.data_issue import DataIssue
    from app.models.export import Export
    from app.models.project import Project
    from app.models.quality_report import QualityReport
    from app.models.schema_profile import SchemaProfile
    from app.models.suggestion import Suggestion


class Dataset(Base):
    """Một dataset (file đã upload) thuộc một project.

    file_type: 'csv' | 'xlsx' | 'xls'. current_version_id trỏ tới phiên bản đang dùng;
    undo = đổi current_version_id về parent_version_id.
    """

    __tablename__ = "datasets"
    __table_args__ = (
        CheckConstraint("file_type IN ('csv', 'xlsx', 'xls')", name="ck_datasets_file_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    encoding: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "dataset_versions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="datasets_current_version_id_fkey",
        ),
        nullable=True,
        index=True,
    )
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship(
        back_populates="dataset",
        cascade="all, delete-orphan",
        passive_deletes=True,
        foreign_keys="DatasetVersion.dataset_id",
    )
    current_version: Mapped["DatasetVersion | None"] = relationship(
        foreign_keys=[current_version_id], post_update=True
    )


class DatasetVersion(Base):
    """Một phiên bản dữ liệu của dataset (hỗ trợ undo/redo qua parent_version_id)."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "version_number", name="uq_dataset_versions_dataset_id_version_number"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="versions", foreign_keys=[dataset_id])
    parent_version: Mapped["DatasetVersion | None"] = relationship(remote_side="DatasetVersion.id")
    schema_profiles: Mapped[list["SchemaProfile"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True
    )
    data_issues: Mapped[list["DataIssue"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True
    )
    quality_report: Mapped["QualityReport | None"] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    exports: Mapped[list["Export"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", passive_deletes=True
    )
