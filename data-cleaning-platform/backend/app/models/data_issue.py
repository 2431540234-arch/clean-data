"""Model DataIssue: lỗi dữ liệu do detector phát hiện trên một phiên bản dataset."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class DataIssue(Base):
    """Một lỗi dữ liệu. row_index = None nghĩa là lỗi ở mức cả cột.

    issue_type: duplicate | missing | outlier | invalid_format | type_mismatch | inconsistent.
    severity: low | medium | high. status: open | fixed | ignored.
    """

    __tablename__ = "data_issues"
    __table_args__ = (
        CheckConstraint(
            "issue_type IN ('duplicate', 'missing', 'outlier', 'invalid_format', "
            "'type_mismatch', 'inconsistent')",
            name="ck_data_issues_issue_type",
        ),
        CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_data_issues_severity"),
        CheckConstraint("status IN ('open', 'fixed', 'ignored')", name="ck_data_issues_status"),
        Index("ix_data_issues_version_id_issue_type", "version_id", "issue_type"),
        Index("ix_data_issues_version_id_column_name", "version_id", "column_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issue_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    current_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship(back_populates="data_issues")
