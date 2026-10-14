"""Đồng hồ (gauge) hiển thị điểm chất lượng dữ liệu bằng Plotly."""


def render_quality_gauge(score: float) -> None:
    """Hiển thị gauge Plotly cho điểm chất lượng (0-100).

    Gợi ý cách làm: dùng plotly.graph_objects.Figure(go.Indicator(mode="gauge+number",
    value=score, gauge={"axis": {"range": [0, 100]}})), render bằng st.plotly_chart.
    """
    raise NotImplementedError("TODO: render gauge Plotly cho điểm chất lượng.")
