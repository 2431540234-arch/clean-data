"""Truy vấn DB cho bảng suggestions."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.suggestion import Suggestion


def list_for_version(db: Session, version_id: int) -> list[Suggestion]:
    """Lấy toàn bộ gợi ý của một phiên bản dataset (theo thứ tự sinh ra)."""
    stmt = select(Suggestion).where(Suggestion.version_id == version_id).order_by(Suggestion.id)
    return list(db.scalars(stmt))


def get_by_id(db: Session, suggestion_id: int) -> Suggestion | None:
    """Lấy một gợi ý theo id."""
    return db.get(Suggestion, suggestion_id)


def create_suggestion(
    db: Session,
    version_id: int,
    source: str,
    proposed_rule: dict[str, Any],
    explanation: str,
    suggestion_type: str = "rule",
    issue_id: int | None = None,
    target_column: str | None = None,
    confidence: float | None = None,
    commit: bool = True,
) -> Suggestion:
    """Tạo một gợi ý mới với status mặc định 'pending'."""
    suggestion = Suggestion(
        version_id=version_id,
        source=source,
        proposed_rule=proposed_rule,
        explanation=explanation,
        suggestion_type=suggestion_type,
        issue_id=issue_id,
        target_column=target_column,
        confidence=confidence,
        status="pending",
    )
    db.add(suggestion)
    if commit:
        db.commit()
        db.refresh(suggestion)
    else:
        db.flush()
    return suggestion


def update_status(
    db: Session, suggestion: Suggestion, status: str, reviewer_id: int | None = None
) -> Suggestion:
    """Cập nhật trạng thái gợi ý ('accepted' hoặc 'rejected') kèm người và thời điểm duyệt."""
    suggestion.status = status
    suggestion.reviewed_by = reviewer_id
    suggestion.reviewed_at = datetime.now(UTC)
    db.flush()
    return suggestion
