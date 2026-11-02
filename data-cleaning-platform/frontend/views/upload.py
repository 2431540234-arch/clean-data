"""Trang Tải lên: tải lên file CSV/Excel, chọn sheet nếu là Excel."""

import streamlit as st

from components.ui import page_shell

page_shell("Tải lên", "Tải file CSV/Excel lên để bắt đầu làm sạch")

st.info(
    "TODO: chọn project, dùng st.file_uploader để chọn file CSV/Excel, gọi POST "
    "/api/v1/datasets/upload; nếu Excel có nhiều sheet thì cho chọn sheet qua POST "
    "/api/v1/datasets/{id}/select-sheet; hiển thị preview_rows trả về."
)
