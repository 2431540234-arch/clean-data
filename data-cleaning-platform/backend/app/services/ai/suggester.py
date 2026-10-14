"""Sinh gợi ý rule JSON từ kết quả profiling, dùng AIClient + validator."""

from app.schemas.rule import RuleSet
from app.schemas.suggestion import SuggestionOut


def generate_suggestions(version_id: int) -> list[SuggestionOut]:
    """Sinh danh sách gợi ý (AI + rule tĩnh) cho một phiên bản dataset.

    Gợi ý cách làm:
    1. Lấy profiling + kết quả detectors của version_id.
    2. Gọi app.services.ai.client.AIClient.complete_json với prompt từ
       app.services.ai.prompts.build_suggestion_prompt.
    3. Validate JSON trả về bằng app.services.ai.validator trước khi lưu vào DB
       (bảng suggestions) qua app.repositories.suggestion_repo.
    """
    raise NotImplementedError(
        "TODO: kết hợp profiling + AI để sinh suggestion, validate trước khi lưu DB."
    )


def mask_rule_to_text(rule_set: RuleSet) -> str:
    """Chuyển RuleSet thành mô tả ngắn gọn (dùng khi hiển thị log/debug)."""
    raise NotImplementedError("TODO: chuyển RuleSet thành chuỗi mô tả ngắn gọn.")
