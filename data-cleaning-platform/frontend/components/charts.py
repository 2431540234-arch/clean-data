"""Các biểu đồ Plotly dùng chung: tỉ lệ thiếu dữ liệu theo cột, cơ cấu kiểu dữ liệu.

Biểu đồ dùng theme="streamlit" để nền/chữ theo theme của ứng dụng; chỉ đặt bảng màu series.
"""

from collections import Counter
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.labels import type_label

_PRIMARY = "#2563EB"
_PALETTE = ["#2563EB", "#60A5FA", "#94A3B8", "#16A34A", "#D97706", "#DC2626", "#7C3AED"]
_ROW_HEIGHT = 34
_MIN_HEIGHT = 160
_NUMERIC_SHARE = 0.9  # tỉ lệ giá trị là số tối thiểu để vẽ histogram
_MAX_CATEGORIES = 20
# Tên mục nằm ở chú thích (không vẽ trên lát cắt) để không bị cắt chữ trên màn hình hẹp.
_DONUT_LAYOUT = {
    "showlegend": True,
    "legend": {"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.05},
    "margin": {"l": 0, "r": 0, "t": 10, "b": 10},
}
_MIN_AXIS_PERCENT = 10  # trục tỉ lệ thiếu tối thiểu 0-10% để thanh nhỏ vẫn đọc được


def render_missing_ratio_chart(column_profiles: list[dict[str, Any]]) -> None:
    """Biểu đồ thanh ngang tỉ lệ thiếu (null_ratio) theo cột, cột thiếu nhiều nhất ở trên."""
    rows = sorted(column_profiles, key=lambda c: c["null_ratio"], reverse=True)
    axis_max = min(100, max(_MIN_AXIS_PERCENT, max(c["null_ratio"] for c in rows) * 100 * 1.4))
    figure = px.bar(
        x=[c["null_ratio"] * 100 for c in rows],
        y=[c["column_name"] for c in rows],
        orientation="h",
        text=[f"{c['null_ratio'] * 100:.1f}%".replace(".", ",") for c in rows],
        color_discrete_sequence=[_PRIMARY],
        labels={"x": "Tỉ lệ thiếu (%)", "y": "Cột"},
    )
    figure.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:.1f}%")
    figure.update_layout(
        height=max(_MIN_HEIGHT, _ROW_HEIGHT * len(rows) + 70),
        margin={"l": 0, "r": 40, "t": 10, "b": 0},
        yaxis={"autorange": "reversed", "title": None},
        xaxis={"range": [0, axis_max], "ticksuffix": "%"},
    )
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)


def render_type_chart(column_profiles: list[dict[str, Any]]) -> None:
    """Biểu đồ vành khuyên cơ cấu số cột theo kiểu dữ liệu suy luận."""
    counts = Counter(type_label(c["inferred_type"]) for c in column_profiles)
    figure = go.Figure(
        go.Pie(
            labels=list(counts),
            values=list(counts.values()),
            hole=0.55,
            marker={"colors": _PALETTE},
            textinfo="value",
            sort=False,
        )
    )
    figure.update_layout(height=340, **_DONUT_LAYOUT)
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)


def render_distribution_chart(values: list[Any], column_name: str) -> None:
    """Biểu đồ phân bố giá trị của một cột: histogram cho số, thanh cho giá trị rời rạc.

    Không có dữ liệu thì không hiện gì (không khung trống, không thông báo). Hiện chưa trang nào
    gọi vì backend chưa có endpoint đọc dữ liệu của version (docs/BACKEND_TODO.md, mục 2 #3).
    """
    values = [v for v in values if v not in (None, "")]
    if not values:
        return
    numbers = pd.to_numeric(pd.Series(values), errors="coerce")
    if numbers.notna().mean() >= _NUMERIC_SHARE:
        figure = px.histogram(
            x=numbers.dropna(),
            color_discrete_sequence=[_PRIMARY],
            labels={"x": column_name, "count": "Số dòng"},
        )
        figure.update_layout(yaxis_title="Số dòng", bargap=0.05)
    else:
        counts = Counter(str(v) for v in values).most_common(_MAX_CATEGORIES)
        figure = px.bar(
            x=[name for name, _ in counts],
            y=[count for _, count in counts],
            color_discrete_sequence=[_PRIMARY],
            labels={"x": column_name, "y": "Số dòng"},
        )
    figure.update_layout(margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=320)
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)


def render_donut_chart(
    items: list[tuple[str, int | float]], colors: list[str] | None = None
) -> None:
    """Biểu đồ vành khuyên cho các cặp (nhãn, giá trị); bỏ qua mục có giá trị 0."""
    shown = [(label, value) for label, value in items if value]
    if not shown:
        return
    figure = go.Figure(
        go.Pie(
            labels=[label for label, _ in shown],
            values=[value for _, value in shown],
            hole=0.55,
            marker={"colors": colors or _PALETTE},
            textinfo="value",
            sort=False,
        )
    )
    figure.update_layout(height=300, **_DONUT_LAYOUT)
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)
