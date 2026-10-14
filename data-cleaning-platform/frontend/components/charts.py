"""Các biểu đồ Plotly dùng chung: tỉ lệ thiếu dữ liệu theo cột, phân bố giá trị."""

from typing import Any


def render_missing_ratio_chart(column_profiles: list[dict[str, Any]]) -> None:
    """Biểu đồ cột thể hiện null_ratio của từng cột.

    Gợi ý cách làm: dùng plotly.express.bar(df, x="column_name", y="null_ratio").
    """
    raise NotImplementedError("TODO: render biểu đồ tỉ lệ thiếu dữ liệu theo cột.")


def render_distribution_chart(values: list[Any], column_name: str) -> None:
    """Biểu đồ phân bố giá trị của một cột (histogram cho số, bar cho category).

    Gợi ý cách làm: dùng plotly.express.histogram.
    """
    raise NotImplementedError("TODO: render biểu đồ phân bố giá trị của một cột.")
