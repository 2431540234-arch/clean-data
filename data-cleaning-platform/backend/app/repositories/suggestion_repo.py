"""Truy vấn DB cho bảng suggestions."""

from typing import Any

from sqlalchemy.orm import Session

from app.models.suggestion import Suggestion


def list_for_version(db: Session, version_id: int) -> list[Suggestion]:
    """Lấy toàn bộ gợi ý của một phiên bản dataset."""
    raise NotImplementedError("TODO: select Suggestion where version_id = version_id.")


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
) -> Suggestion:
    """Tạo một gợi ý mới với status mặc định 'pending'."""
    raise NotImplementedError("TODO: tạo Suggestion mới, add/commit/refresh.")


def update_status(db: Session, suggestion: Suggestion, status: str) -> Suggestion:
    """Cập nhật trạng thái gợi ý ('accepted' hoặc 'rejected')."""
    raise NotImplementedError(
        "TODO: cập nhật suggestion.status, reviewed_by, reviewed_at và commit."
    )
