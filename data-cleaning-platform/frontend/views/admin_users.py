"""Trang Quản trị người dùng: chỉ admin. Xem danh sách, khóa/mở, đổi quyền user."""

import streamlit as st

from components.ui import page_shell

page_shell("Quản trị người dùng", "Khóa/mở tài khoản, đổi quyền, đặt lại mật khẩu", admin=True)

st.info(
    "TODO: gọi GET /api/v1/admin/users, hiển thị bằng components.user_table; cho phép "
    "khóa/mở (PATCH is_active) và đổi quyền (PATCH role) từng user."
)
