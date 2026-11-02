"""Trang Tổng quan dữ liệu: kết quả profiling và các lỗi đã phát hiện."""

import streamlit as st

from components.ui import page_shell

page_shell("Tổng quan dữ liệu", "Kết quả profiling và các lỗi đã phát hiện")

st.info(
    "TODO: chọn dataset/version, gọi POST rồi GET /api/v1/profiling/{version_id} để hiển "
    "thị bảng thống kê từng cột, dùng components.charts để vẽ biểu đồ tỉ lệ thiếu dữ liệu "
    "và phân bố giá trị."
)
