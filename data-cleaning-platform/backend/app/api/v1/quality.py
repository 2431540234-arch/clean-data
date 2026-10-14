"""API lấy điểm chất lượng dữ liệu (data quality score) của một phiên bản dataset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.quality import QualityReportOut

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/{version_id}", response_model=QualityReportOut)
def get_quality_report(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QualityReportOut:
    """Lấy báo cáo điểm chất lượng đã tính của một phiên bản dataset (tính nếu chưa có)."""
    raise NotImplementedError(
        "TODO: dùng app.services.quality.compute_quality_score, lưu/đọc cache DB."
    )
