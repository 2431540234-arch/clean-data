"""Định dạng hiển thị kiểu Việt Nam: ngày giờ (UTC+7), số, phần trăm, dung lượng."""

from datetime import UTC, datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))
_EMPTY = "—"


def format_datetime(value: str | None) -> str:
    """ISO 8601 -> "dd/MM/yyyy HH:mm" theo giờ Việt Nam; chuỗi rỗng/không hợp lệ -> "—"."""
    if not value:
        return _EMPTY
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return _EMPTY
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(VN_TZ).strftime("%d/%m/%Y %H:%M")


def format_date(value: str | None) -> str:
    """ISO 8601 -> "dd/MM/yyyy" theo giờ Việt Nam."""
    text = format_datetime(value)
    return text.split(" ")[0] if text != _EMPTY else text


def format_number(value: int | float | None) -> str:
    """Số nguyên có dấu chấm ngăn cách hàng nghìn: 1234567 -> "1.234.567"."""
    if value is None:
        return _EMPTY
    return f"{round(value):,}".replace(",", ".")


def format_percent(ratio: float | None, digits: int = 1) -> str:
    """Tỉ lệ 0..1 -> phần trăm dùng dấu phẩy thập phân: 0.1234 -> "12,3%"."""
    if ratio is None:
        return _EMPTY
    return f"{ratio * 100:.{digits}f}".replace(".", ",") + "%"


def format_bytes(size: int | None) -> str:
    """Dung lượng dễ đọc: 1536 -> "1,5 KB"."""
    if size is None:
        return _EMPTY
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            text = f"{value:.0f}" if unit == "B" else f"{value:.1f}".replace(".", ",")
            return f"{text} {unit}"
        value /= 1024
    return _EMPTY


def to_vn_datetime(value: str | None) -> datetime | None:
    """ISO 8601 -> datetime theo giờ Việt Nam; None nếu rỗng hoặc không hợp lệ."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(VN_TZ)
