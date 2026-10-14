"""Model Export: lịch sử xuất dữ liệu sạch của một phiên bản (CSV/Excel/Parquet)."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import DatasetVersion


class Export(Base):
    """Một lần xuất file. format: csv | xlsx | parquet."""

    __tablename__ = "exports"
    __table_args__ = (
        CheckConstraint("format IN ('csv', 'xlsx', 'parquet')", name="ck_exports_format"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    include_quality_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    exported_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    version: Mapped["DatasetVersion"] = relationship(back_populates="exports")
