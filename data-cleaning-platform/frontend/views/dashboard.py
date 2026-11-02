"""Trang Dashboard: tổng quan các project và dataset của người dùng."""

import streamlit as st

from components.ui import page_shell

page_shell("Dashboard", "Tổng quan các project và dataset của bạn")

st.info(
    "TODO: hiển thị danh sách project của người dùng (GET /api/v1/projects), số dataset, "
    "điểm chất lượng trung bình, nút tạo project mới."
)
