"""Chạy profiling cho toàn bộ dataset: thống kê null_ratio, unique_ratio, sample_values mỗi cột."""

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ColumnProfile:
    """Kết quả profiling của một cột."""

    column_name: str
    inferred_type: str
    null_ratio: float
    unique_ratio: float
    sample_values: list[Any]


def profile_dataframe(df: pd.DataFrame, sample_size: int = 5) -> list[ColumnProfile]:
    """Chạy profiling cho toàn bộ cột trong df.

    Gợi ý cách làm: với mỗi cột, tính null_ratio = số null / tổng số dòng,
    unique_ratio = số giá trị unique / tổng số dòng, lấy sample_size giá trị mẫu
    không rỗng, và gọi app.services.profiling.type_inference.infer_column_type.
    """
    raise NotImplementedError(
        "TODO: lặp qua từng cột của df, tính null_ratio/unique_ratio/sample_values/inferred_type."
    )
