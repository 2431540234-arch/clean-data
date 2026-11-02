"""Trang Mapping cột: gợi ý ánh xạ tên cột file upload với schema chuẩn."""

import streamlit as st

from components.ui import page_shell

page_shell("Mapping cột", "Ánh xạ tên cột của file với schema chuẩn")

st.info(
    "TODO: gọi POST /api/v1/mapping/{version_id}/suggest, hiển thị bảng mapping gợi ý "
    "(cột nguồn -> cột đích), cho phép người dùng sửa tay trước khi xác nhận."
)
