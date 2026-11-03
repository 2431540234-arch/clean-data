"""API chạy & lấy kết quả profiling schema của một phiên bản dataset."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.issue import DataIssueOut
from app.schemas.profile import ProfilingResult, SchemaProfileOut
from app.services import access, profiling_service

router = APIRouter(prefix="/profiling", tags=["profiling"])


def _result(version_id: int, profiles) -> ProfilingResult:
    return ProfilingResult(
        version_id=version_id,
        columns=[SchemaProfileOut.model_validate(p) for p in profiles],
    )


@router.post("/{version_id}/run", response_model=ProfilingResult)
def run_profiling(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfilingResult:
    """Chạy profiling + phát hiện lỗi cho một phiên bản và lưu kết quả (chạy rồi thì trả lại)."""
    version = access.get_owned_version(db, current_user, version_id)
    return _result(version.id, profiling_service.run_profiling(db, version))


@router.get("/{version_id}", response_model=ProfilingResult)
def get_profiling_result(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfilingResult:
    """Lấy kết quả profiling đã lưu của một phiên bản (404 nếu chưa chạy)."""
    version = access.get_owned_version(db, current_user, version_id)
    return _result(version.id, profiling_service.get_profiles_or_404(db, version.id))


@router.get("/{version_id}/issues", response_model=list[DataIssueOut])
def list_issues(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DataIssueOut]:
    """Danh sách lỗi dữ liệu đã phát hiện (404 nếu chưa chạy profiling)."""
    version = access.get_owned_version(db, current_user, version_id)
    return profiling_service.list_issues(db, version.id)
