"""Model SchemaProfile: thống kê từng cột của một phiên bản dataset (kết quả profiling)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class SchemaProfile(Base):
    """Kết quả profiling của một cột trong một phiên bản dataset cụ thể."""

    __tablename__ = "schema_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(50), nullable=False)
    null_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sample_values: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship()
