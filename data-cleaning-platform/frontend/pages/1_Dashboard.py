"""Trang Dashboard: tổng quan các project và dataset của người dùng."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Dashboard", page_icon="📊")
init_state()
require_login()

st.title("📊 Dashboard")
st.info(
    "TODO: hiển thị danh sách project của người dùng (GET /api/v1/projects), "
    "số dataset, điểm chất lượng trung bình, nút tạo project mới."
)
