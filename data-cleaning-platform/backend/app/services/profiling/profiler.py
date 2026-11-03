"""Chạy profiling cho toàn bộ dataset: thống kê null_ratio, unique_ratio, sample_values mỗi cột."""

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.services.profiling import values as v
from app.services.profiling.type_inference import infer_column_type


@dataclass
class ColumnProfile:
    """Kết quả profiling của một cột."""

    column_name: str
    inferred_type: str
    null_ratio: float
    unique_ratio: float
    sample_values: list[Any]
    column_index: int = 0
    null_count: int = 0
    unique_count: int = 0
    min_value: str | None = None
    max_value: str | None = None
    mean_value: float | None = None
    detected_format: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _date_summary(values: pd.Series) -> tuple[str | None, str | None, str | None]:
    """(định dạng phát hiện, ngày nhỏ nhất, ngày lớn nhất) của một cột ngày."""
    parsed = {value: v.parse_date(value) for value in values.unique()}
    counts: Counter[str] = Counter()
    moments = []
    for value, count in values.value_counts().items():
        result = parsed[value]
        if result is None:
            continue
        counts[result[0]] += int(count)
        moments.append(result[1])
    if not counts:
        return None, None, None
    labels = [label for label, _ in counts.most_common()]
    detected = labels[0] if len(labels) == 1 else "Nhiều định dạng: " + ", ".join(labels)
    return detected, min(moments).strftime("%Y-%m-%d"), max(moments).strftime("%Y-%m-%d")


def profile_column(series: pd.Series, index: int, total_rows: int, sample_size: int = 5):
    """Thống kê một cột."""
    name = str(series.name)
    mask = v.null_mask(series)
    null_count = int(mask.sum())
    present = series[~mask]
    stripped = present.astype(str).str.strip()
    inferred = infer_column_type(series)
    unique_count = int(stripped.nunique())

    profile = ColumnProfile(
        column_name=name,
        column_index=index,
        inferred_type=inferred,
        null_count=null_count,
        unique_count=unique_count,
        null_ratio=null_count / total_rows if total_rows else 0.0,
        unique_ratio=unique_count / total_rows if total_rows else 0.0,
        sample_values=[str(x) for x in present.drop_duplicates().head(sample_size)],
    )
    if inferred in ("integer", "float"):
        numbers = [n for n in (v.to_number(x) for x in stripped.unique()) if n is not None]
        if numbers:
            profile.min_value = v.format_number(min(numbers))
            profile.max_value = v.format_number(max(numbers))
            # trung bình theo từng dòng (không theo giá trị duy nhất)
            all_numbers = stripped.map(v.to_number).dropna()
            profile.mean_value = round(float(all_numbers.mean()), 2)
    elif inferred == "date":
        profile.detected_format, profile.min_value, profile.max_value = _date_summary(stripped)
    return profile


def profile_dataframe(df: pd.DataFrame, sample_size: int = 5) -> list[ColumnProfile]:
    """Chạy profiling cho toàn bộ cột trong df (theo thứ tự cột)."""
    total = len(df)
    return [profile_column(df[col], i, total, sample_size) for i, col in enumerate(df.columns)]
