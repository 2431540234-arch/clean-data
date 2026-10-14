"""Kiểm tra JSON do AI trả về có đúng DSL rule hay không, trước khi lưu/hiển thị cho người dùng.

Đây là lớp bảo vệ quan trọng: dù AI có "ảo giác" sinh ra op lạ hay tham số sai, hệ thống
cũng không được lưu/thi hành rule đó.
"""

from typing import Any

from pydantic import ValidationError

from app.schemas.rule import RuleSet


class AIRuleValidationError(Exception):
    """Lỗi khi JSON do AI trả về không hợp lệ theo DSL rule."""


def validate_ai_rule_json(raw_json: dict[str, Any]) -> RuleSet:
    """Validate dict JSON (do AI trả về) thành RuleSet hợp lệ.

    Raises:
        AIRuleValidationError: nếu JSON không đúng cấu trúc hoặc chứa op không hợp lệ.
    """
    try:
        return RuleSet.model_validate(raw_json)
    except ValidationError as exc:
        raise AIRuleValidationError(f"JSON do AI trả về không hợp lệ theo DSL rule: {exc}") from exc
