"""API chạy & lấy kết quả profiling schema của một phiên bản dataset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.profile import ProfilingResult

router = APIRouter(prefix="/profiling", tags=["profiling"])


@router.post("/{version_id}/run", response_model=ProfilingResult)
def run_profiling(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfilingResult:
    """Chạy profiling cho một phiên bản dataset và lưu kết quả vào bảng schema_profiles.

    Gợi ý cách làm: đọc DataFrame qua app.services.storage, gọi
    app.services.profiling.profiler.profile_dataframe, lưu kết quả vào DB.
    """
    raise NotImplementedError("TODO: chạy profiling và lưu kết quả vào DB.")


@router.get("/{version_id}", response_model=ProfilingResult)
def get_profiling_result(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfilingResult:
    """Lấy kết quả profiling đã lưu của một phiên bản dataset."""
    raise NotImplementedError("TODO: lấy SchemaProfile theo version_id từ DB.")
