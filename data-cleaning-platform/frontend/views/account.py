"""Trang Tài khoản: xem thông tin cá nhân, đổi mật khẩu."""

import streamlit as st

from components.ui import page_shell

page_shell("Tài khoản", "Thông tin cá nhân và mật khẩu")

st.info(
    "TODO: hiển thị thông tin và thêm form đổi mật khẩu gọi POST /api/v1/auth/change- "
    "password (mật khẩu cũ + mật khẩu mới)."
)
