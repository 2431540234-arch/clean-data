"""Trang Upload: tải lên file CSV/Excel, chọn sheet nếu là Excel."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Upload dữ liệu", page_icon="⬆️")
init_state()
require_login()

st.title("⬆️ Upload dữ liệu")
st.info(
    "TODO: chọn project, dùng st.file_uploader để chọn file CSV/Excel, gọi "
    "POST /api/v1/datasets/upload; nếu Excel có nhiều sheet thì cho chọn sheet "
    "qua POST /api/v1/datasets/{id}/select-sheet; hiển thị preview_rows trả về."
)
