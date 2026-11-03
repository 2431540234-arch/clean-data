"""Thông tin từ HTTP request dùng chung (hiện chỉ có địa chỉ IP của client)."""

from fastapi import Request

from app.core.config import settings

_MAX_IP_LENGTH = 45  # khớp audit_logs.ip_address (đủ cho IPv6)


def client_ip(request: Request) -> str | None:
    """IP của client để ghi nhật ký.

    Chỉ tin header `X-Forwarded-For` khi cấu hình `TRUST_PROXY_HEADERS=true` (backend nằm sau
    reverse proxy tin cậy); nếu không, header này do client tự đặt nên có thể giả mạo.
    """
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first[:_MAX_IP_LENGTH]
    return request.client.host[:_MAX_IP_LENGTH] if request.client else None
