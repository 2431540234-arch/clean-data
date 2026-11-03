"""Op chuẩn hóa ngày tháng."""

from datetime import datetime
from typing import Any

import pandas as pd

from app.services.profiling.values import parse_date_with_preference
from app.services.rules.ops.common import map_cells, require_column
from app.services.rules.registry import RuleError, register

DEFAULT_OUTPUT_FORMAT = "%Y-%m-%d"


@register("standardize_date")
def standardize_date(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đổi mọi ngày hợp lệ về một định dạng.

    params:
        output_format: định dạng strftime đầu ra (mặc định "%Y-%m-%d").
        dayfirst: với ngày mơ hồ như 03/04/2020, True đọc là ngày 3 tháng 4 (mặc định), False
            đọc là tháng 3 ngày 4. Giá trị không phải ngày hợp lệ được giữ nguyên.
    """
    require_column(df, column)
    output = params.get("output_format", DEFAULT_OUTPUT_FORMAT)
    if not isinstance(output, str) or not output or "%" not in output:
        raise RuleError("output_format phải là định dạng ngày kiểu strftime, ví dụ %Y-%m-%d.")
    try:
        datetime(2000, 1, 2).strftime(output)
    except ValueError as exc:
        raise RuleError("output_format không hợp lệ.") from exc
    dayfirst = bool(params.get("dayfirst", True))

    def convert(text: str) -> str:
        parsed = parse_date_with_preference(text, dayfirst)
        return parsed.strftime(output) if parsed else text

    return map_cells(df, column, convert)
