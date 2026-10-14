"""Model CleaningOperation: một lần áp dụng rule, nối phiên bản trước với phiên bản sau."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class CleaningOperation(Base):
    """Thao tác làm sạch đã áp dụng: from_version -> to_version, kèm rule/gợi ý gốc."""

    __tablename__ = "cleaning_operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("rules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    suggestion_id: Mapped[int | None] = mapped_column(
        ForeignKey("suggestions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    rows_affected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    applied_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    from_version: Mapped["DatasetVersion"] = relationship(foreign_keys=[from_version_id])
    to_version: Mapped["DatasetVersion"] = relationship(foreign_keys=[to_version_id])
