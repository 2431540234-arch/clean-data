"""Trang Tổng quan dữ liệu: kết quả profiling và các lỗi đã phát hiện."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Tổng quan dữ liệu", page_icon="🔍")
init_state()
require_login()

st.title("🔍 Tổng quan dữ liệu")
st.info(
    "TODO: chọn dataset/version, gọi POST rồi GET /api/v1/profiling/{version_id} "
    "để hiển thị bảng thống kê từng cột, dùng components.charts để vẽ biểu đồ "
    "tỉ lệ thiếu dữ liệu và phân bố giá trị."
)
