"""API xem trước dữ liệu trước/sau khi áp dụng rule (chưa ghi vào DB thật)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.preview import PreviewRequest, PreviewResult

router = APIRouter(prefix="/preview", tags=["preview"])


@router.post("", response_model=PreviewResult)
def preview_rules(
    payload: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PreviewResult:
    """Chạy dry_run rule_set và trả về diff trước/sau trên một mẫu dữ liệu."""
    raise NotImplementedError("TODO: dùng app.services.preview.compute_preview.")
