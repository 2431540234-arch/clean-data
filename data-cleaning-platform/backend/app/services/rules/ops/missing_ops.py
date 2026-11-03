"""Op xử lý dữ liệu thiếu."""

from collections import Counter
from statistics import fmean, median
from typing import Any

import pandas as pd

from app.services.profiling.values import format_number, is_null, to_number
from app.services.rules.ops.common import cell_text, require_choice, require_column
from app.services.rules.registry import RuleError, register

STRATEGIES = ("constant", "mean", "median", "mode", "ffill", "bfill")


@register("fill_missing")
def fill_missing(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Điền các ô thiếu (ô trống hoặc null-token như "N/A", "-") của một cột.

    params:
        strategy: "constant" (dùng params.value), "mean", "median" (cần cột có giá trị số),
            "mode" (giá trị phổ biến nhất), "ffill" (lấy giá trị phía trên), "bfill" (phía dưới).
    Ô không có gì để điền (ví dụ ffill ở dòng đầu) được giữ nguyên.
    """
    require_column(df, column)
    strategy = require_choice(params, "strategy", STRATEGIES, "constant")
    values = [cell_text(v) for v in df[column]]
    missing = [is_null(v) for v in values]
    present = [v.strip() for v, m in zip(values, missing, strict=True) if not m]

    fills: list[str | None]
    if strategy == "constant":
        if params.get("value") is None or str(params["value"]) == "":
            raise RuleError("Chiến lược constant cần tham số value khác rỗng.")
        fills = [str(params["value"])] * len(values)
    elif strategy in ("mean", "median"):
        numbers = [n for n in (to_number(v) for v in present) if n is not None]
        if not numbers:
            raise RuleError("Cột không có giá trị số để tính trung bình/trung vị.")
        value = fmean(numbers) if strategy == "mean" else median(numbers)
        fills = [format_number(round(value, 4))] * len(values)
    elif strategy == "mode":
        if not present:
            raise RuleError("Cột không có giá trị nào để lấy giá trị phổ biến nhất.")
        fills = [Counter(present).most_common(1)[0][0]] * len(values)
    else:
        order = range(len(values)) if strategy == "ffill" else range(len(values) - 1, -1, -1)
        fills, last = [None] * len(values), None
        for i in order:
            if missing[i]:
                fills[i] = last
            else:
                last = values[i]

    new_values, changed = [], 0
    for current, is_missing, fill in zip(values, missing, fills, strict=True):
        if is_missing and fill is not None:
            new_values.append(fill)
            changed += current != fill
        else:
            new_values.append(current)
    result = df.copy()
    result[column] = new_values
    return result, int(changed)
