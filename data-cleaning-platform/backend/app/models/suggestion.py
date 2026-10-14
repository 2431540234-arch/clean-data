"""Model Suggestion: gợi ý làm sạch (do AI hoặc rule engine sinh ra) chờ user duyệt."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.data_issue import DataIssue
    from app.models.dataset import DatasetVersion


class Suggestion(Base):
    """Một gợi ý làm sạch gắn với một phiên bản dataset (và tùy chọn một lỗi cụ thể).

    suggestion_type: 'fix' | 'rule' | 'column_mapping'. source: 'ai' | 'rule_engine'.
    Mức độ nghiêm trọng nằm ở data_issues.severity (qua issue_id).
    status: 'pending' | 'accepted' | 'rejected'.
    confidence: độ tin cậy 0–1. explanation: giải thích dễ hiểu cho người không chuyên.
    """

    __tablename__ = "suggestions"
    __table_args__ = (
        CheckConstraint(
            "suggestion_type IN ('fix', 'rule', 'column_mapping')",
            name="ck_suggestions_suggestion_type",
        ),
        CheckConstraint("source IN ('ai', 'rule_engine')", name="ck_suggestions_source"),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')", name="ck_suggestions_status"
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_suggestions_confidence",
        ),
        Index("ix_suggestions_version_id_status", "version_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_issues.id", ondelete="SET NULL"), nullable=True, index=True
    )
    suggestion_type: Mapped[str] = mapped_column(String(20), nullable=False, default="rule")
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    proposed_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship(back_populates="suggestions")
    issue: Mapped["DataIssue | None"] = relationship()
