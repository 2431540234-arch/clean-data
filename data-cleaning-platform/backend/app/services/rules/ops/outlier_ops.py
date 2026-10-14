"""Op đánh dấu outlier (không tự xóa dữ liệu, chỉ gắn cờ để người dùng quyết định)."""

from typing import Any

import pandas as pd

from app.services.rules.registry import register


@register("flag_outliers")
def flag_outliers(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đánh dấu các dòng là outlier dựa trên IQR hoặc Z-score, thêm cột cờ "<column>_is_outlier".

    params:
        method: "iqr" | "zscore".
        threshold: hệ số ngưỡng (mặc định 1.5 cho iqr, 3 cho zscore).

    Gợi ý cách làm: tái sử dụng logic trong app.services.detectors.outliers để tính
    ngưỡng, thêm cột boolean đánh dấu, không xóa dòng nào.
    """
    raise NotImplementedError(
        "TODO: tính ngưỡng outlier theo params['method'], thêm cột cờ, "
        "đếm số dòng được đánh dấu là outlier."
    )
