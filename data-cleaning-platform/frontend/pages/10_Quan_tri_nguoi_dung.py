"""Trang Quản trị người dùng: chỉ admin. Xem danh sách, khóa/mở, đổi quyền user."""

import streamlit as st

from components.auth_guard import require_admin
from state import init_state

st.set_page_config(page_title="Quản trị người dùng", page_icon="🛠️")
init_state()
require_admin()

st.title("🛠️ Quản trị người dùng")
st.info(
    "TODO: gọi GET /api/v1/admin/users, hiển thị bằng components.user_table; "
    "cho phép khóa/mở (PATCH is_active) và đổi quyền (PATCH role) từng user."
)
