"""Che dữ liệu cá nhân (PII) trước khi gửi mẫu dữ liệu cho AI provider bên ngoài."""

import re
from typing import Any

from app.services.profiling.values import is_email, looks_like_phone

_PHONE_CLEAN_RE = re.compile(r"[^\d+]")


def mask_value(value: str, kind: str | None = None) -> str:
    """Che một giá trị: email giữ ký tự đầu + tên miền, SĐT giữ 3 số đầu + 2 số cuối.

    kind: kiểu cột nếu đã biết ('email' | 'phone' | 'name' | None = tự đoán theo hình dạng).
    kind == 'name' rút mỗi từ về chữ cái đầu ("Nguyễn Văn An" -> "N. V. A.").
    """
    text = str(value).strip()
    if not text:
        return text
    if kind == "email" or (kind is None and is_email(text)):
        local, _, domain = text.partition("@")
        return f"{local[:1]}***@{domain}" if domain else "***"
    if kind == "phone" or (kind is None and looks_like_phone(text)):
        digits = _PHONE_CLEAN_RE.sub("", text)
        return f"{digits[:3]}***{digits[-2:]}" if len(digits) > 5 else "***"
    if kind == "name":
        return " ".join(f"{word[0]}." for word in text.split() if word)
    return text


def mask_sample_values(sample_values: list[Any], kind: str | None = None) -> list[Any]:
    """Che một phần giá trị nhạy cảm (email, số điện thoại, họ tên) trước khi gửi cho AI."""
    return [mask_value(str(v), kind) for v in sample_values]
