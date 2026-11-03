"""API sinh gợi ý làm sạch dữ liệu và chấp nhận/từ chối gợi ý."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user, get_db
from app.core.request_info import client_ip
from app.models.user import User
from app.repositories import suggestion_repo
from app.schemas.suggestion import (
    SuggestionDecisionRequest,
    SuggestionGenerateRequest,
    SuggestionOut,
)
from app.services import access
from app.services.ai.suggester import generate_suggestions as build_suggestions
from app.services.audit import log_action

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.post("/generate", response_model=list[SuggestionOut])
async def generate_suggestions(
    payload: SuggestionGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestionOut]:
    """Sinh gợi ý mới cho một phiên bản (thay thế gợi ý cũ): quy tắc + AI nếu có cấu hình."""
    version = access.get_owned_version(db, current_user, payload.version_id)
    # Chạy ở thread riêng: phân tích dữ liệu và chờ AI đều chặn, không được khóa event loop.
    suggestions = await run_in_threadpool(
        build_suggestions, db, current_user.id, version, client_ip(request)
    )
    return [SuggestionOut.model_validate(s) for s in suggestions]


@router.get("/by-version/{version_id}", response_model=list[SuggestionOut])
def list_suggestions(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SuggestionOut]:
    """Lấy toàn bộ gợi ý của một phiên bản dataset."""
    version = access.get_owned_version(db, current_user, version_id)
    return [
        SuggestionOut.model_validate(s) for s in suggestion_repo.list_for_version(db, version.id)
    ]


@router.post("/{suggestion_id}/decision", response_model=SuggestionOut)
def decide_suggestion(
    suggestion_id: int,
    payload: SuggestionDecisionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SuggestionOut:
    """Người dùng chấp nhận hoặc từ chối một gợi ý (được đổi ý nhiều lần; chưa áp dụng gì)."""
    suggestion = access.get_owned_suggestion(db, current_user, suggestion_id)
    old_status = suggestion.status
    suggestion_repo.update_status(db, suggestion, payload.decision, current_user.id)
    log_action(
        db,
        current_user.id,
        "suggestion.accept" if payload.decision == "accepted" else "suggestion.reject",
        "suggestion",
        suggestion.id,
        project_id=suggestion.version.dataset.project_id,
        old_value={"status": old_status},
        new_value={"status": suggestion.status},
        ip_address=client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(suggestion)
    return SuggestionOut.model_validate(suggestion)
