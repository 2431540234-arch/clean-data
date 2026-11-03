"""Op xử lý theo dòng: xóa dòng trùng, xóa dòng theo điều kiện."""

from typing import Any

import pandas as pd

from app.services.profiling.values import is_null, to_number
from app.services.rules.ops.common import cell_text, require_choice, require_column
from app.services.rules.registry import RuleError, register

KEEP_CHOICES = ("first", "last")
OPERATORS = ("gt", "lt", "gte", "lte", "eq", "neq", "is_null", "is_not_null")


@register("drop_duplicates")
def drop_duplicates(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa các dòng trùng nhau (so khớp nguyên văn).

    params:
        subset: danh sách cột dùng để so (mặc định null = tất cả cột); nếu không có subset mà
            có `column` thì so theo riêng cột đó.
        keep: "first" (giữ dòng đầu, mặc định) hoặc "last".
    """
    subset = params.get("subset")
    if subset is None and column:
        subset = [column]
    if subset is not None:
        if not isinstance(subset, list) or not subset:
            raise RuleError("subset phải là danh sách tên cột.")
        for name in subset:
            require_column(df, name)
    keep = require_choice(params, "keep", KEEP_CHOICES, "first")
    mask = df.duplicated(subset=subset, keep=keep)
    return df[~mask], int(mask.sum())


def _compare(operator: str, value: str, target: Any) -> bool:
    """True nếu ô `value` thỏa điều kiện (ô sẽ bị xóa)."""
    if operator == "is_null":
        return is_null(value)
    if operator == "is_not_null":
        return not is_null(value)
    if is_null(value):
        return False  # so sánh với ô thiếu không có nghĩa: giữ lại
    left = to_number(value)
    right = to_number(str(target)) if target is not None else None
    if operator in ("gt", "lt", "gte", "lte"):
        if left is None or right is None:
            return False
        return {"gt": left > right, "lt": left < right, "gte": left >= right, "lte": left <= right}[
            operator
        ]
    same = left == right if left is not None and right is not None else value.strip() == str(target)
    return same if operator == "eq" else not same


@register("drop_rows_where")
def drop_rows_where(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa các dòng mà ô của `column` thỏa điều kiện.

    params:
        operator: gt | lt | gte | lte | eq | neq | is_null | is_not_null.
        value: giá trị so sánh (không cần với is_null/is_not_null). So số khi cả hai là số,
            ngược lại so chuỗi.
    """
    require_column(df, column)
    operator = require_choice(params, "operator", OPERATORS, None)
    target = params.get("value")
    if operator not in ("is_null", "is_not_null") and target is None:
        raise RuleError("Toán tử so sánh cần tham số value.")
    mask = df[column].map(cell_text).map(lambda v: _compare(operator, v, target)).astype(bool)
    return df[~mask], int(mask.sum())
