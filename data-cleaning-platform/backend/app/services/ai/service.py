"""Điểm gọi AI duy nhất của hệ thống: kiểm tra đã cấu hình chưa, gọi, ghi nhật ký ai_requests.

AI chỉ là phần bổ sung tùy chọn: không có khóa API, hết thời gian hoặc AI trả lời hỏng thì hàm
trả None và người gọi dùng kết quả từ quy tắc. Nhật ký chỉ lưu số liệu (nhà cung cấp, mô hình,
mục đích, số token, độ trễ, trạng thái), KHÔNG lưu dữ liệu người dùng hay khóa API.
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai_request import AIRequest
from app.services.ai.client import AIClient, AIError

logger = logging.getLogger(__name__)

MAX_ERROR_LENGTH = 300


def get_client() -> AIClient:
    """Tạo client AI theo cấu hình hiện tại (test thay hàm này bằng client giả)."""
    return AIClient()


def ai_available() -> bool:
    """Đã có nhà cung cấp và khóa API hợp lệ."""
    return get_client().is_configured()


def call_ai(
    db: Session,
    user_id: int | None,
    purpose: str,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any] | None:
    """Gọi AI, ghi nhật ký rồi trả dict JSON; không dùng được AI thì trả None (không ném lỗi).

    Commit ngay để nhật ký còn lại kể cả khi thao tác gọi nó thất bại về sau, nên người gọi phải
    gọi hàm này TRƯỚC khi có thay đổi dở dang trong session.
    """
    client = get_client()
    if not client.is_configured():
        return None
    try:
        response = client.complete_json(system_prompt, user_prompt)
    except AIError as exc:
        _log(db, user_id, client, purpose, "error", exc.latency_ms, error=exc.message)
        return None
    except Exception:  # noqa: BLE001 - AI không bao giờ được làm hỏng chức năng chính
        logger.exception("Lỗi không lường trước khi gọi AI")
        return None
    _log(
        db,
        user_id,
        client,
        purpose,
        "success",
        response.latency_ms,
        tokens=(response.input_tokens, response.output_tokens),
        model=response.model,
    )
    return response.data


def _log(
    db: Session,
    user_id: int | None,
    client: AIClient,
    purpose: str,
    status: str,
    latency_ms: int | None,
    tokens: tuple[int | None, int | None] = (None, None),
    error: str | None = None,
    model: str | None = None,
) -> None:
    db.add(
        AIRequest(
            user_id=user_id,
            provider=client.provider,
            model=model or client.model,
            purpose=purpose,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            latency_ms=latency_ms,
            status=status,
            error_message=(error or None) and error[:MAX_ERROR_LENGTH],
        )
    )
    db.commit()
