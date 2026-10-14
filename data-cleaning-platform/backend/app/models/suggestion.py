"""Model Suggestion: gợi ý rule làm sạch (do AI hoặc rule tĩnh sinh ra) chờ user duyệt."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class Suggestion(Base):
    """Một gợi ý làm sạch gắn với một phiên bản dataset.

    source: 'ai' hoặc 'rule'. severity: 'high' | 'medium' | 'low'.
    status: 'pending' | 'accepted' | 'rejected'.
    """

    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="low")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship()
