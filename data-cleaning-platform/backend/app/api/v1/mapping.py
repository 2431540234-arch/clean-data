"""API gợi ý mapping tên cột (fuzzy matching tầng 1, AI tầng 2)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter(prefix="/mapping", tags=["mapping"])


@router.post("/{version_id}/suggest")
def suggest_mapping(
    version_id: int,
    target_schema: list[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str | None]:
    """Gợi ý mapping tên cột của dataset version với target_schema.

    Gợi ý cách làm: dùng app.services.mapping.matcher.match_columns (tầng 1),
    với các cột chưa khớp dùng app.services.ai.mapper.suggest_column_mapping_with_ai (tầng 2).
    """
    raise NotImplementedError("TODO: kết hợp mapping tầng 1 (fuzzy) và tầng 2 (AI).")
