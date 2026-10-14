"""Schema cho gợi ý làm sạch dữ liệu (do AI hoặc rule tĩnh sinh ra)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.rule import RuleSet


class SuggestionOut(BaseModel):
    """Một gợi ý làm sạch trả về cho client, gồm giải thích và rule JSON đề xuất."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    source: Literal["ai", "rule"]
    rule_json: RuleSet
    explanation: str
    severity: Literal["high", "medium", "low"]
    status: Literal["pending", "accepted", "rejected"]
    created_at: datetime


class SuggestionGenerateRequest(BaseModel):
    """Yêu cầu sinh gợi ý mới cho một phiên bản dataset (dựa trên kết quả profiling)."""

    version_id: int


class SuggestionDecisionRequest(BaseModel):
    """Người dùng chấp nhận hoặc từ chối một gợi ý."""

    decision: Literal["accepted", "rejected"]
