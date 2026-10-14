"""Model QualityReport: điểm chất lượng dữ liệu (data quality score) của một phiên bản."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class QualityReport(Base):
    """Báo cáo chất lượng, mỗi phiên bản dataset có tối đa một báo cáo (version_id unique).

    overall_score và 4 tiêu chí thành phần đều nằm trong khoảng 0–100.
    """

    __tablename__ = "quality_reports"
    __table_args__ = (
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="ck_quality_overall"),
        CheckConstraint(
            "completeness IS NULL OR (completeness >= 0 AND completeness <= 100)",
            name="ck_quality_completeness",
        ),
        CheckConstraint(
            "uniqueness IS NULL OR (uniqueness >= 0 AND uniqueness <= 100)",
            name="ck_quality_uniqueness",
        ),
        CheckConstraint(
            "validity IS NULL OR (validity >= 0 AND validity <= 100)", name="ck_quality_validity"
        ),
        CheckConstraint(
            "consistency IS NULL OR (consistency >= 0 AND consistency <= 100)",
            name="ck_quality_consistency",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness: Mapped[float | None] = mapped_column(Float, nullable=True)
    uniqueness: Mapped[float | None] = mapped_column(Float, nullable=True)
    validity: Mapped[float | None] = mapped_column(Float, nullable=True)
    consistency: Mapped[float | None] = mapped_column(Float, nullable=True)
    issue_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship(back_populates="quality_report")
