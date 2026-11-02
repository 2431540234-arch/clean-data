"""Trang Nhật ký hoạt động (audit log): hành động của chính mình hoặc toàn hệ thống (admin)."""

import streamlit as st

from components.ui import page_shell

page_shell("Nhật ký hoạt động", "Các hành động đã thực hiện trên hệ thống")

st.info(
    "TODO: user thường gọi GET /api/v1/audit/me; nếu is_admin() có thêm tùy chọn xem toàn "
    "hệ thống qua GET /api/v1/audit/all. Hiển thị bằng st.dataframe."
)
