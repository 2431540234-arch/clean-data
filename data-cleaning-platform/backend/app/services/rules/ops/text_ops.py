"""Các op xử lý văn bản: trim_whitespace, change_case, replace_values.

trim_whitespace là op mẫu hoàn chỉnh, minh họa chữ ký chuẩn mà mọi op khác phải tuân theo.
"""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("trim_whitespace")
def trim_whitespace(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Xóa khoảng trắng dư ở đầu/cuối giá trị của một cột.

    Args:
        df: DataFrame đầu vào.
        column: tên cột cần xử lý (bắt buộc).
        params: không dùng cho op này, giữ lại để đồng nhất chữ ký.

    Returns:
        Tuple (DataFrame mới, số dòng có giá trị bị thay đổi).
    """
    if column not in df.columns:
        raise ValueError(f"Cột '{column}' không tồn tại trong dữ liệu.")

    result_df = df.copy()
    original = result_df[column]
    trimmed = original.apply(lambda v: v.strip() if isinstance(v, str) else v)

    affected_mask = (original != trimmed) & ~(original.isna() & trimmed.isna())
    affected_rows = int(affected_mask.sum())

    result_df[column] = trimmed
    return result_df, affected_rows


@register("change_case")
def change_case(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Chuyển đổi chữ hoa/thường của một cột.

    params:
        mode: "upper" | "lower" | "title" | "capitalize".
    """
    raise NotImplementedError(
        "TODO: áp dụng str.upper/lower/title/capitalize theo params['mode'], "
        "trả về (df mới, số dòng bị thay đổi)."
    )


@register("replace_values")
def replace_values(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Thay thế các giá trị cụ thể trong một cột theo mapping.

    params:
        mapping: dict[str, str] - giá trị cũ -> giá trị mới.
            Ví dụ dùng để chuẩn hóa "HCM" / "TP.HCM" -> "TP. Hồ Chí Minh".
    """
    raise NotImplementedError(
        "TODO: dùng df[column].replace(params['mapping']) và đếm số dòng thay đổi."
    )
