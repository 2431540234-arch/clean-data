"""Trang Thống kê hệ thống: chỉ admin. Số user, dataset, lượt gọi AI, điểm chất lượng TB."""

import streamlit as st

from components.ui import page_shell

page_shell("Thống kê hệ thống", "Số liệu tổng quan toàn hệ thống", admin=True)

st.info(
    "TODO: gọi GET /api/v1/admin/stats, hiển thị các chỉ số bằng st.metric và biểu đồ " "Plotly."
)
