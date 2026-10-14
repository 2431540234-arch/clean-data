"""Model SchemaProfile: thống kê từng cột của một phiên bản dataset (kết quả profiling)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class SchemaProfile(Base):
    """Kết quả profiling của một cột trong một phiên bản dataset cụ thể.

    null_count/unique_count là số tuyệt đối; null_ratio/unique_ratio là tỉ lệ (0–1) trên
    row_count của version. min_value/max_value lưu dạng chuỗi để dùng được cho mọi kiểu cột.
    """

    __tablename__ = "schema_profiles"
    __table_args__ = (
        UniqueConstraint("version_id", "column_name", name="uq_schema_profiles_version_id_column"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    column_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    inferred_type: Mapped[str] = mapped_column(String(50), nullable=False)
    null_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    null_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    min_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    mean_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_values: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    detected_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship(back_populates="schema_profiles")
