"""Trang Audit log: xem lại các hành động của chính mình (user) hoặc toàn hệ thống (admin)."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state, is_admin

st.set_page_config(page_title="Audit log", page_icon="📝")
init_state()
require_login()

st.title("📝 Audit log")
st.info(
    "TODO: user thường gọi GET /api/v1/audit/me; nếu is_admin() có thêm tùy chọn xem "
    "toàn hệ thống qua GET /api/v1/audit/all. Hiển thị bằng st.dataframe."
)
