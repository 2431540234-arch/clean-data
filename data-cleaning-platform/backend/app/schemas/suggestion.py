"""Schema cho gợi ý làm sạch dữ liệu (do AI hoặc rule tĩnh sinh ra)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.rule import RuleSet


class SuggestionOut(BaseModel):
    """Một gợi ý làm sạch trả về cho client: giải thích + rule JSON đề xuất.

    Mức độ nghiêm trọng xem ở lỗi gắn qua issue_id.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    issue_id: int | None
    suggestion_type: Literal["fix", "rule", "column_mapping"]
    source: Literal["ai", "rule_engine"]
    target_column: str | None
    proposed_rule: RuleSet
    explanation: str
    confidence: float | None
    status: Literal["pending", "accepted", "rejected"]
    reviewed_by: int | None
    reviewed_at: datetime | None
    created_at: datetime


class SuggestionGenerateRequest(BaseModel):
    """Yêu cầu sinh gợi ý mới cho một phiên bản dataset (dựa trên kết quả profiling)."""

    version_id: int


class SuggestionDecisionRequest(BaseModel):
    """Người dùng chấp nhận hoặc từ chối một gợi ý."""

    decision: Literal["accepted", "rejected"]
