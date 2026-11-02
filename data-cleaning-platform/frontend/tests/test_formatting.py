"""components.formatting: định dạng ngày giờ, số, phần trăm, dung lượng kiểu Việt Nam."""

from components.formatting import (
    format_bytes,
    format_date,
    format_datetime,
    format_number,
    format_percent,
)


def test_datetime_is_converted_to_vietnam_time():
    assert format_datetime("2026-09-12T03:20:00+00:00") == "12/09/2026 10:20"
    assert format_datetime("2026-09-12T20:00:00Z") == "13/09/2026 03:00"
    assert format_date("2026-09-12T20:00:00Z") == "13/09/2026"


def test_datetime_without_timezone_is_treated_as_utc():
    assert format_datetime("2026-01-01T00:00:00") == "01/01/2026 07:00"


def test_datetime_empty_or_invalid():
    assert format_datetime(None) == "—"
    assert format_datetime("không phải ngày") == "—"
    assert format_date(None) == "—"


def test_number_percent_bytes():
    assert format_number(1234567) == "1.234.567"
    assert format_number(None) == "—"
    assert format_percent(0.1234) == "12,3%"
    assert format_percent(0, 0) == "0%"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1536) == "1,5 KB"
    assert format_bytes(5 * 1024 * 1024) == "5,0 MB"
