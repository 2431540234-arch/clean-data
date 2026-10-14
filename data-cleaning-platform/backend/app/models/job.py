"""Model Job: tác vụ xử lý nền (profiling, phát hiện lỗi, gợi ý AI, áp dụng rule, export)."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Job(Base):
    """Một tác vụ nền.

    job_type: profile | detect_issues | ai_suggest | apply_rules | export.
    status: pending | running | done | failed. progress: 0–100.
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "job_type IN ('profile', 'detect_issues', 'ai_suggest', 'apply_rules', 'export')",
            name="ck_jobs_job_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'running', 'done', 'failed')", name="ck_jobs_status"
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_jobs_progress"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_type: Mapped[str] = mapped_column(String(30), nullable=False)
    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=True, index=True
    )
    version_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
