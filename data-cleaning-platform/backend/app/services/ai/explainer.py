"""Giải thích lỗi dữ liệu bằng tiếng Việt dễ hiểu cho người dùng không chuyên kỹ thuật."""

from app.services.detectors.base import DetectionIssue


def explain_issue(issue: DetectionIssue) -> str:
    """Trả về mô tả tiếng Việt dễ hiểu cho một DetectionIssue.

    Gợi ý cách làm: với lỗi đơn giản có thể dùng template có sẵn (không cần gọi AI);
    với lỗi phức tạp hơn có thể gọi app.services.ai.client.AIClient với prompt từ
    app.services.ai.prompts.build_explanation_prompt.
    """
    raise NotImplementedError("TODO: sinh mô tả tiếng Việt cho DetectionIssue.")
