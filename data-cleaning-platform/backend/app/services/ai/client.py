"""Client gọi OpenAI/Anthropic, có retry/timeout. Chỉ dùng để lấy JSON, không exec() kết quả."""

import json
import re
import time
from dataclasses import dataclass
from typing import Any

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_fixed

from app.core.config import settings

SUPPORTED_PROVIDERS = ("anthropic", "openai")
MAX_OUTPUT_TOKENS = 2000
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class AIError(Exception):
    """Lỗi khi gọi AI (mạng, hết thời gian, nhà cung cấp trả lỗi, JSON hỏng...)."""

    def __init__(self, message: str, latency_ms: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.latency_ms = latency_ms


@dataclass
class AIResponse:
    """Kết quả một lần gọi AI thành công."""

    data: dict[str, Any]
    provider: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


def parse_json_object(text: str) -> dict[str, Any]:
    """Lấy một JSON object từ câu trả lời của AI (chịu được rào ```json và lời dẫn thừa)."""
    cleaned = _FENCE_RE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise AIError("AI không trả về JSON.")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIError("AI trả về JSON không hợp lệ.") from exc
    if not isinstance(data, dict):
        raise AIError("AI phải trả về một JSON object.")
    return data


def _is_transient(exc: BaseException) -> bool:
    """Lỗi tạm thời đáng thử lại: mất kết nối, hết thời gian, quá tải/5xx của nhà cung cấp."""
    names = {cls.__name__ for cls in type(exc).__mro__}
    return bool(
        names & {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError"}
    )


class AIClient:
    """Wrapper gọi AI provider (OpenAI hoặc Anthropic) theo cấu hình AI_PROVIDER."""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = (provider or settings.AI_PROVIDER).strip().lower()

    @property
    def api_key(self) -> str:
        key = (
            settings.ANTHROPIC_API_KEY if self.provider == "anthropic" else settings.OPENAI_API_KEY
        )
        return key.strip()

    @property
    def model(self) -> str:
        return settings.AI_MODEL

    def is_configured(self) -> bool:
        """Có nhà cung cấp hợp lệ và có khóa API chưa (không có khóa thì tính năng AI tự tắt)."""
        return self.provider in SUPPORTED_PROVIDERS and bool(self.api_key)

    def complete_json(self, system_prompt: str, user_prompt: str) -> AIResponse:
        """Gọi AI provider, yêu cầu trả lời ở dạng JSON, parse và trả về dict (kèm số liệu gọi).

        Chỉ thử lại (tối đa 2 lần) với lỗi tạm thời. Mọi lỗi khác được gói thành AIError với
        thông báo không chứa khóa API.
        """
        if not self.is_configured():
            raise AIError("Chưa cấu hình khóa API cho AI.")
        started = time.monotonic()
        try:
            text, tokens_in, tokens_out = self._call_with_retry(system_prompt, user_prompt)
            data = parse_json_object(text)
        except AIError as exc:
            exc.latency_ms = int((time.monotonic() - started) * 1000)
            raise
        except (
            Exception
        ) as exc:  # noqa: BLE001 - lỗi của SDK/mạng, gói lại để caller xử lý thống nhất
            raise AIError(
                f"Gọi AI thất bại ({type(exc).__name__}).",
                int((time.monotonic() - started) * 1000),
            ) from exc
        return AIResponse(
            data=data,
            provider=self.provider,
            model=self.model,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        reraise=True,
    )
    def _call_with_retry(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, int | None, int | None]:
        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        return self._call_openai(system_prompt, user_prompt)

    def _call_anthropic(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, int | None, int | None]:
        import anthropic

        client = anthropic.Anthropic(
            api_key=self.api_key, timeout=settings.AI_TIMEOUT_SECONDS, max_retries=0
        )
        response = client.messages.create(
            model=self.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        usage = getattr(response, "usage", None)
        return text, getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)

    def _call_openai(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, int | None, int | None]:
        import openai

        client = openai.OpenAI(
            api_key=self.api_key, timeout=settings.AI_TIMEOUT_SECONDS, max_retries=0
        )
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        usage = getattr(response, "usage", None)
        return (
            response.choices[0].message.content or "",
            getattr(usage, "prompt_tokens", None),
            getattr(usage, "completion_tokens", None),
        )
