"""API lấy điểm chất lượng dữ liệu (data quality score) của một phiên bản dataset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.quality import QualityReportOut
from app.services import access, quality_service

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/{version_id}", response_model=QualityReportOut)
async def get_quality_report(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QualityReportOut:
    """Lấy báo cáo điểm chất lượng của một phiên bản (tính và lưu lần đầu, sau đó đọc lại)."""
    version = access.get_owned_version(db, current_user, version_id)
    report = await run_in_threadpool(quality_service.get_or_compute, db, version)
    return QualityReportOut.model_validate(report)
