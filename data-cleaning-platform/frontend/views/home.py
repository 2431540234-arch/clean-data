"""Trang chủ: lời chào và điểm bắt đầu của quy trình làm sạch dữ liệu."""

import streamlit as st

from components.navigation import PRODUCT_TAGLINE
from components.ui import page_shell
from state import get_current_user

page_shell("Trang chủ", PRODUCT_TAGLINE)

user = get_current_user() or {}
st.write(f"Xin chào, **{user.get('full_name') or user.get('email')}**!")
st.write(
    "Dùng menu bên trái để tải dữ liệu lên, xem tổng quan, nhận gợi ý làm sạch, "
    "xem lịch sử phiên bản và xuất dữ liệu."
)
