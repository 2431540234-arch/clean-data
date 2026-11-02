"""Các biểu đồ Plotly dùng chung: tỉ lệ thiếu dữ liệu theo cột, cơ cấu kiểu dữ liệu.

Biểu đồ dùng theme="streamlit" để nền/chữ theo theme của ứng dụng; chỉ đặt bảng màu series.
"""

from collections import Counter
from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.labels import type_label

_PRIMARY = "#2563EB"
_PALETTE = ["#2563EB", "#60A5FA", "#94A3B8", "#16A34A", "#D97706", "#DC2626", "#7C3AED"]
_ROW_HEIGHT = 34
_MIN_HEIGHT = 160
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
            textinfo="label+value",
            sort=False,
        )
    )
    figure.update_layout(height=320, showlegend=False, margin={"l": 0, "r": 0, "t": 10, "b": 10})
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)


def render_distribution_chart(values: list[Any], column_name: str) -> None:
    """Biểu đồ phân bố giá trị của một cột (histogram cho số, bar cho category).

    Gợi ý cách làm: dùng plotly.express.histogram.

    TODO(backend): chưa dùng ở đâu vì backend chưa có endpoint đọc dữ liệu của version
    (docs/BACKEND_TODO.md, mục 2 #3), nên chưa có `values` để vẽ.
    """
    raise NotImplementedError("TODO: render biểu đồ phân bố giá trị của một cột.")
