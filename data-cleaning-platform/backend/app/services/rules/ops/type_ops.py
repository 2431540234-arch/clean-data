"""Op ép kiểu dữ liệu của một cột."""

from typing import Any

import pandas as pd

from app.services.profiling.values import format_number, is_null, to_number
from app.services.rules.ops.common import map_cells, require_choice, require_column
from app.services.rules.registry import RuleError, register

TARGET_TYPES = ("int", "float", "str")
ON_ERROR = ("coerce", "raise")
MAX_EXAMPLES_IN_ERROR = 3


@register("cast_type")
def cast_type(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Ép cột về dạng số nguyên, số thực hoặc chuỗi (dữ liệu vẫn lưu dạng chữ đã chuẩn hóa).

    params:
        target_type: "int" | "float" | "str".
        on_error: "coerce" (mặc định) đặt ô không ép được thành ô trống; "raise" báo lỗi và
            không áp dụng gì. Với "int", số có phần thập phân (3.7) cũng tính là không ép được.
    """
    require_column(df, column)
    target = require_choice(params, "target_type", TARGET_TYPES, None)
    on_error = require_choice(params, "on_error", ON_ERROR, "coerce")
    failures: list[str] = []

    def convert(text: str) -> str:
        if is_null(text):
            return ""  # "N/A", "-"... là ô thiếu: thống nhất thành ô trống
        if target == "str":
            return text.strip()
        number = to_number(text)
        if number is None or (target == "int" and not number.is_integer()):
            failures.append(text)
            return ""
        return str(int(number)) if target == "int" else format_number(number)

    result, changed = map_cells(df, column, convert, skip_null=False)
    if failures and on_error == "raise":
        shown = ", ".join(f"“{v}”" for v in dict.fromkeys(failures[:MAX_EXAMPLES_IN_ERROR]))
        raise RuleError(f"Có giá trị không ép được sang {target} (vd. {shown}).")
    return result, changed
