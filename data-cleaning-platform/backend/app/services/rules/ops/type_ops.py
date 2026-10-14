"""Op chuyển đổi kiểu dữ liệu của một cột."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("cast_type")
def cast_type(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Chuyển đổi kiểu dữ liệu của một cột.

    params:
        target_type: "int" | "float" | "str" | "bool" | "datetime".
        on_error: "coerce" (đặt NaN khi lỗi) | "raise".

    Gợi ý cách làm: dùng pandas.to_numeric/to_datetime/astype tùy target_type, đếm
    số dòng chuyển đổi thất bại (trở thành NaN khi on_error="coerce").
    """
    raise NotImplementedError(
        "TODO: ép kiểu df[column] theo params['target_type'], xử lý lỗi theo params['on_error']."
    )
