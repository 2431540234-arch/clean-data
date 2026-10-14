"""Op xử lý theo cột: đổi tên cột, xóa cột."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("rename_column")
def rename_column(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đổi tên một cột.

    params:
        new_name: tên cột mới.

    Gợi ý cách làm: df.rename(columns={column: params['new_name']}); số dòng ảnh hưởng
    = số dòng của df (toàn bộ dữ liệu được "ảnh hưởng" về schema) hoặc 0 tùy quy ước.
    """
    raise NotImplementedError("TODO: dùng df.rename(columns={column: params['new_name']}).")


@register("drop_column")
def drop_column(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa một cột khỏi dataset.

    Gợi ý cách làm: df.drop(columns=[column]); số dòng ảnh hưởng = số dòng của df.
    """
    raise NotImplementedError("TODO: dùng df.drop(columns=[column]).")
