"""Trang Mapping cột: gợi ý ánh xạ tên cột file upload với schema chuẩn."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Mapping cột", page_icon="🔗")
init_state()
require_login()

st.title("🔗 Mapping cột")
st.info(
    "TODO: gọi POST /api/v1/mapping/{version_id}/suggest, hiển thị bảng mapping gợi ý "
    "(cột nguồn -> cột đích), cho phép người dùng sửa tay trước khi xác nhận."
)
