"""Op xử lý dữ liệu thiếu (missing values)."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("fill_missing")
def fill_missing(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Điền giá trị thiếu trong một cột.

    params:
        strategy: "constant" | "mean" | "median" | "mode" | "ffill" | "bfill".
        value: giá trị dùng khi strategy = "constant".

    Gợi ý cách làm: tính giá trị điền theo strategy (vd df[column].mean() cho "mean"),
    dùng df[column].fillna(...), đếm số dòng trước đó là null.
    """
    raise NotImplementedError(
        "TODO: điền giá trị thiếu theo params['strategy'], đếm số dòng đã được điền."
    )
