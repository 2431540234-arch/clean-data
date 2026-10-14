"""Trang Xuất dữ liệu: xuất phiên bản hiện tại ra CSV/Excel kèm báo cáo chất lượng."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Xuất dữ liệu", page_icon="📤")
init_state()
require_login()

st.title("📤 Xuất dữ liệu")
st.info(
    "TODO: hiển thị components.quality_gauge cho điểm chất lượng hiện tại, nút xuất "
    "CSV (GET /api/v1/export/{version_id}/csv) và Excel "
    "(GET /api/v1/export/{version_id}/excel) qua st.download_button."
)
