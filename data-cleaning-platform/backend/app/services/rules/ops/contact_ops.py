"""Op chuẩn hóa số điện thoại và email."""

import re
from typing import Any

import pandas as pd
import phonenumbers

from app.services.profiling.values import is_email
from app.services.rules.ops.common import map_cells, require_choice, require_column
from app.services.rules.registry import RuleError, register

PHONE_FORMATS = ("E164", "NATIONAL", "INTERNATIONAL")
_PHONE_STRIP_RE = re.compile(r"[\s.\-()]")


@register("standardize_phone")
def standardize_phone(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đổi số điện thoại hợp lệ về một kiểu duy nhất.

    params:
        region: mã quốc gia để hiểu số viết kiểu trong nước (mặc định "VN").
        output_format: "E164" (+84901234567), "NATIONAL" (0901234567, chỉ chữ số) hoặc
            "INTERNATIONAL" (+84 90 123 4567). Số không hợp lệ được giữ nguyên.
    """
    require_column(df, column)
    region = str(params.get("region", "VN")).upper()
    if region not in phonenumbers.SUPPORTED_REGIONS:
        raise RuleError(f"Mã vùng “{region}” không được hỗ trợ.")
    fmt = require_choice(params, "output_format", PHONE_FORMATS, "E164")

    def convert(text: str) -> str:
        try:
            number = phonenumbers.parse(_PHONE_STRIP_RE.sub("", text), region)
        except phonenumbers.NumberParseException:
            return text
        if not phonenumbers.is_valid_number(number):
            return text
        if fmt == "E164":
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
        if fmt == "INTERNATIONAL":
            return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        national = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.NATIONAL)
        return re.sub(r"\D", "", national)

    return map_cells(df, column, convert)


@register("standardize_email")
def standardize_email(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Cắt khoảng trắng và đổi email về chữ thường.

    params:
        drop_invalid: True thì email sai cú pháp bị đặt thành ô trống; False (mặc định) thì giữ
            nguyên giá trị sai.
    """
    require_column(df, column)
    drop_invalid = bool(params.get("drop_invalid", False))

    def convert(text: str) -> str:
        cleaned = text.strip().lower()
        if is_email(cleaned):
            return cleaned
        return "" if drop_invalid else text

    return map_cells(df, column, convert)
