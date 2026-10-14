"""Op chuẩn hóa số điện thoại và email."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("standardize_phone")
def standardize_phone(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Chuẩn hóa số điện thoại về một định dạng thống nhất.

    params:
        region: mã vùng mặc định khi số không có mã quốc gia, ví dụ "VN".
        output_format: "E164" | "NATIONAL" | "INTERNATIONAL" (dùng phonenumbers.PhoneNumberFormat).

    Gợi ý cách làm: dùng thư viện `phonenumbers` để parse theo params['region'], format lại
    theo params['output_format']; số không parse được thì giữ nguyên và không tính là affected.
    """
    raise NotImplementedError(
        "TODO: dùng phonenumbers.parse/format_number để chuẩn hóa số điện thoại."
    )


@register("standardize_email")
def standardize_email(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Chuẩn hóa email: trim khoảng trắng, chuyển về chữ thường, validate cú pháp.

    params:
        drop_invalid: bool - nếu True, các email không hợp lệ sẽ bị đặt thành None
            thay vì giữ nguyên giá trị gốc.

    Gợi ý cách làm: dùng thư viện `email_validator` để kiểm tra & chuẩn hóa.
    """
    raise NotImplementedError(
        "TODO: dùng email_validator.validate_email để chuẩn hóa/kiểm tra cú pháp email."
    )
