"""Trang Thống kê hệ thống: chỉ admin. Số user, dataset, lượt gọi AI, điểm chất lượng TB."""

import streamlit as st

from components.auth_guard import require_admin
from state import init_state

st.set_page_config(page_title="Thống kê hệ thống", page_icon="📈")
init_state()
require_admin()

st.title("📈 Thống kê hệ thống")
st.info(
    "TODO: gọi GET /api/v1/admin/stats, hiển thị các chỉ số bằng st.metric và "
    "biểu đồ Plotly (ví dụ phân bố điểm chất lượng theo thời gian)."
)
