"""Đồng hồ (gauge) hiển thị điểm chất lượng dữ liệu bằng Plotly."""

import plotly.graph_objects as go
import streamlit as st

# Ngưỡng nhãn điểm: khớp các dải màu của gauge.
SCORE_GOOD = 80
SCORE_FAIR = 60

_BAR = "#2563EB"
_BANDS = [
    {"range": [0, SCORE_FAIR], "color": "#fecaca"},
    {"range": [SCORE_FAIR, SCORE_GOOD], "color": "#fde68a"},
    {"range": [SCORE_GOOD, 100], "color": "#bbf7d0"},
]


def score_label(score: float) -> tuple[str, str]:
    """(nhãn tiếng Việt, loại badge) theo điểm: Tốt / Trung bình / Cần cải thiện."""
    if score >= SCORE_GOOD:
        return "Tốt", "success"
    if score >= SCORE_FAIR:
        return "Trung bình", "warning"
    return "Cần cải thiện", "error"


def render_quality_gauge(score: float) -> None:
    """Hiển thị gauge Plotly cho điểm chất lượng (0-100); con số hiển thị riêng ở thẻ bên cạnh."""
    figure = go.Figure(
        go.Indicator(
            mode="gauge",
            value=score,
            gauge={
                "axis": {"range": [0, 100], "tickvals": [0, SCORE_FAIR, SCORE_GOOD, 100]},
                "bar": {"color": _BAR, "thickness": 0.35},
                "steps": _BANDS,
            },
        )
    )
    figure.update_layout(height=230, margin={"l": 24, "r": 48, "t": 16, "b": 8})
    st.plotly_chart(figure, theme="streamlit", use_container_width=True)
