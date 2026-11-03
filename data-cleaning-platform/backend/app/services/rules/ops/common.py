"""Hàm dùng chung cho các op: kiểm tra cột/tham số và áp một hàm lên từng ô.

Quy ước chung của mọi op: dữ liệu là chuỗi, ô thiếu (None/NaN/chuỗi rỗng/null-token như "N/A")
được BỎ QUA và giữ nguyên, trừ các op có mục đích riêng cho ô thiếu (fill_missing, replace_values,
drop_rows_where). Op trả về DataFrame mới (không sửa df đầu vào) và số dòng bị thay đổi.
"""

from collections.abc import Callable
from typing import Any

import pandas as pd

from app.services.profiling.values import is_null
from app.services.rules.registry import RuleError


def require_column(df: pd.DataFrame, column: str | None) -> str:
    """Cột bắt buộc phải có trong df."""
    if not column or column not in df.columns:
        raise RuleError(f"Cột “{column}” không tồn tại trong dữ liệu.")
    return column


def require_choice(params: dict[str, Any], key: str, choices: tuple[str, ...], default: str | None):
    """Giá trị của tham số `key` phải nằm trong `choices` (thiếu thì dùng default)."""
    value = params.get(key, default)
    if value not in choices:
        raise RuleError(f"Tham số {key} phải là một trong: {', '.join(choices)}.")
    return value


def cell_text(value: Any) -> str:
    """Giá trị ô dưới dạng chuỗi ('' cho None/NaN)."""
    return "" if value is None or (isinstance(value, float) and value != value) else str(value)


def map_cells(
    df: pd.DataFrame,
    column: str,
    func: Callable[[str], str],
    skip_null: bool = True,
) -> tuple[pd.DataFrame, int]:
    """Áp `func` lên từng giá trị DUY NHẤT của cột; trả (df mới, số dòng có giá trị đổi)."""
    old = df[column].map(cell_text)
    mapping = {}
    for value in old.unique():
        mapping[value] = value if (skip_null and is_null(value)) else func(value)
    new = old.map(mapping)
    changed = int((old != new).sum())
    result = df.copy()
    result[column] = new
    return result, changed
