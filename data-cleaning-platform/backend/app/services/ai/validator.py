"""Kiểm tra JSON do AI trả về có đúng DSL rule hay không, trước khi lưu/hiển thị cho người dùng.

Đây là lớp bảo vệ quan trọng: dù AI có "ảo giác" sinh ra op lạ hay tham số sai, hệ thống
cũng không được lưu/thi hành rule đó.
"""

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from app.schemas.rule import RuleSet
from app.services.ai.prompts import AI_ALLOWED_OPS

logger = logging.getLogger(__name__)

MAX_AI_SUGGESTIONS = 8
MAX_STEPS_PER_SUGGESTION = 3
MAX_EXPLANATION_LENGTH = 500


class AIRuleValidationError(Exception):
    """Lỗi khi JSON do AI trả về không hợp lệ theo DSL rule."""


@dataclass
class AISuggestion:
    """Một gợi ý của AI đã qua kiểm tra."""

    issue_id: int | None
    column: str | None
    explanation: str
    confidence: float | None
    rule_set: RuleSet


def validate_ai_rule_json(raw_json: dict[str, Any]) -> RuleSet:
    """Validate dict JSON (do AI trả về) thành RuleSet hợp lệ.

    Raises:
        AIRuleValidationError: nếu JSON không đúng cấu trúc hoặc chứa op không hợp lệ.
    """
    try:
        return RuleSet.model_validate(raw_json)
    except ValidationError as exc:
        raise AIRuleValidationError(f"JSON do AI trả về không hợp lệ theo DSL rule: {exc}") from exc


def _confidence(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return round(min(1.0, max(0.0, float(value))), 2)


def validate_ai_suggestions(
    raw: dict[str, Any], columns: set[str], issue_ids: set[int]
) -> list[AISuggestion]:
    """Lọc các gợi ý hợp lệ trong câu trả lời của AI; gợi ý hỏng bị bỏ riêng, không hỏng cả lô.

    Một gợi ý được giữ khi: có 1-3 bước, mỗi bước dùng op trong AI_ALLOWED_OPS và cột có thật
    (trừ drop_duplicates), explanation là chuỗi không rỗng. issue_id lạ bị bỏ (đặt None).
    """
    items = raw.get("suggestions") if isinstance(raw, dict) else None
    if not isinstance(items, list):
        return []
    accepted: list[AISuggestion] = []
    for item in items[: MAX_AI_SUGGESTIONS * 2]:
        try:
            if not isinstance(item, dict):
                raise AIRuleValidationError("gợi ý không phải object")
            rule_set = validate_ai_rule_json(item.get("rule") or {})
            _check_steps(rule_set, columns)
            explanation = item.get("explanation")
            if not isinstance(explanation, str) or not explanation.strip():
                raise AIRuleValidationError("thiếu explanation")
            issue_id = item.get("issue_id")
            column = item.get("column")
            accepted.append(
                AISuggestion(
                    issue_id=(
                        issue_id if isinstance(issue_id, int) and issue_id in issue_ids else None
                    ),
                    column=column if isinstance(column, str) and column in columns else None,
                    explanation=explanation.strip()[:MAX_EXPLANATION_LENGTH],
                    confidence=_confidence(item.get("confidence")),
                    rule_set=rule_set,
                )
            )
        except AIRuleValidationError as exc:
            logger.info("Bỏ một gợi ý AI không hợp lệ: %s", str(exc)[:200])
        if len(accepted) >= MAX_AI_SUGGESTIONS:
            break
    return accepted


def _check_steps(rule_set: RuleSet, columns: set[str]) -> None:
    if not 1 <= len(rule_set.steps) <= MAX_STEPS_PER_SUGGESTION:
        raise AIRuleValidationError("số bước không hợp lệ")
    for step in rule_set.steps:
        if step.op not in AI_ALLOWED_OPS:
            raise AIRuleValidationError(f"op '{step.op}' không được AI đề xuất")
        if step.column is not None and step.column not in columns:
            raise AIRuleValidationError(f"cột '{step.column}' không tồn tại")
