"""API xem trước dữ liệu trước/sau khi áp dụng rule (chưa ghi vào DB thật)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.preview import PreviewRequest, PreviewResult
from app.services import access
from app.services.preview import compute_preview

router = APIRouter(prefix="/preview", tags=["preview"])


@router.post("", response_model=PreviewResult)
async def preview_rules(
    payload: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreviewResult:
    """Chạy dry_run rule_set và trả về diff trước/sau trên một mẫu dữ liệu (không ghi gì)."""
    version = access.get_owned_version(db, current_user, payload.version_id)
    return await run_in_threadpool(compute_preview, version, payload.rule_set, payload.sample_rows)
