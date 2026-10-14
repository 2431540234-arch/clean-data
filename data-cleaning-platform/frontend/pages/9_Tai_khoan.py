"""Trang Tài khoản: xem thông tin cá nhân, đổi mật khẩu."""

import streamlit as st

from components.auth_guard import require_login
from state import get_current_user, init_state

st.set_page_config(page_title="Tài khoản", page_icon="👤")
init_state()
require_login()

st.title("👤 Tài khoản của tôi")
user = get_current_user()
st.write(f"**Email:** {user.get('email')}")
st.write(f"**Họ tên:** {user.get('full_name')}")
st.write(f"**Quyền:** {user.get('role')}")

st.info(
    "TODO: thêm form đổi mật khẩu gọi POST /api/v1/auth/change-password "
    "(mật khẩu cũ + mật khẩu mới)."
)
