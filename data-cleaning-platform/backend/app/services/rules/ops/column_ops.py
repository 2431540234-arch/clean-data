"""Op xử lý theo cột: đổi tên cột, xóa cột."""

from typing import Any

import pandas as pd

from app.services.rules.ops.common import require_column
from app.services.rules.registry import RuleError, register

MAX_COLUMN_NAME_LENGTH = 255


@register("rename_column")
def rename_column(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đổi tên một cột (params.new_name). Không ảnh hưởng dòng nào nên số dòng ảnh hưởng là 0."""
    require_column(df, column)
    new_name = str(params.get("new_name") or "").strip()
    if not new_name:
        raise RuleError("Thiếu tên cột mới (new_name).")
    if len(new_name) > MAX_COLUMN_NAME_LENGTH:
        raise RuleError(f"Tên cột mới dài quá {MAX_COLUMN_NAME_LENGTH} ký tự.")
    if new_name != column and new_name in df.columns:
        raise RuleError(f"Cột “{new_name}” đã tồn tại, không thể đổi tên trùng.")
    return df.rename(columns={column: new_name}), 0


@register("drop_column")
def drop_column(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa một cột khỏi dữ liệu (không được xóa cột cuối cùng)."""
    require_column(df, column)
    if len(df.columns) == 1:
        raise RuleError("Không thể xóa cột cuối cùng của dữ liệu.")
    return df.drop(columns=[column]), 0
