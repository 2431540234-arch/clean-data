"""Op xử lý theo dòng: xóa trùng lặp, xóa dòng theo điều kiện."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("drop_duplicates")
def drop_duplicates(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa các dòng trùng lặp.

    params:
        subset: list[str] | None - danh sách cột để xác định trùng lặp (None = toàn bộ cột).
        keep: "first" | "last" | False.

    Gợi ý cách làm: dùng df.drop_duplicates(subset=params.get("subset"),
    keep=params.get("keep", "first")), số dòng bị ảnh hưởng = số dòng đã xóa.
    """
    raise NotImplementedError("TODO: dùng df.drop_duplicates theo params['subset']/params['keep'].")


@register("drop_rows_where")
def drop_rows_where(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa các dòng thỏa điều kiện trên một cột.

    params:
        operator: "eq" | "neq" | "gt" | "lt" | "gte" | "lte" | "is_null" | "is_not_null".
        value: giá trị so sánh (không cần cho is_null/is_not_null).

    Gợi ý cách làm: xây mask boolean theo operator rồi df = df[~mask].
    """
    raise NotImplementedError(
        "TODO: xây điều kiện từ params['operator']/params['value'] và xóa các dòng khớp."
    )
