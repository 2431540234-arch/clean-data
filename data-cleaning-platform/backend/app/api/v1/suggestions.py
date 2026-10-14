"""API sinh gợi ý làm sạch dữ liệu và chấp nhận/từ chối gợi ý."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.suggestion import (
    SuggestionDecisionRequest,
    SuggestionGenerateRequest,
    SuggestionOut,
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("/generate", response_model=list[SuggestionOut])
def generate_suggestions(
    payload: SuggestionGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestionOut]:
    """Sinh gợi ý mới cho một phiên bản dataset (dùng AI + rule tĩnh)."""
    raise NotImplementedError("TODO: dùng app.services.ai.suggester.generate_suggestions.")


@router.get("/by-version/{version_id}", response_model=list[SuggestionOut])
def list_suggestions(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestionOut]:
    """Lấy toàn bộ gợi ý của một phiên bản dataset."""
    raise NotImplementedError("TODO: dùng app.repositories.suggestion_repo.list_for_version.")


@router.post("/{suggestion_id}/decision", response_model=SuggestionOut)
def decide_suggestion(
    suggestion_id: int,
    payload: SuggestionDecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SuggestionOut:
    """Người dùng chấp nhận hoặc từ chối một gợi ý."""
    raise NotImplementedError("TODO: cập nhật status gợi ý qua app.repositories.suggestion_repo.")
