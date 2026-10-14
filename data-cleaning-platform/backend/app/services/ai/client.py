"""Client gọi OpenAI/Anthropic, có retry/timeout. Chỉ dùng để lấy JSON, không exec() kết quả."""

from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


class AIClient:
    """Wrapper gọi AI provider (OpenAI hoặc Anthropic) theo cấu hình AI_PROVIDER."""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.AI_PROVIDER

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Gọi AI provider, yêu cầu trả lời ở dạng JSON, parse và trả về dict.

        Gợi ý cách làm: nếu self.provider == "openai" dùng openai.OpenAI(api_key=...)
        .chat.completions.create(response_format={"type": "json_object"}, ...); nếu
        "anthropic" dùng anthropic.Anthropic(api_key=...).messages.create(...) rồi
        parse nội dung text trả về bằng json.loads. Luôn validate kết quả bằng
        app.services.ai.validator trước khi trả lại cho caller.
        """
        raise NotImplementedError(
            "TODO: gọi OpenAI/Anthropic theo settings.AI_PROVIDER, parse JSON kết quả."
        )
