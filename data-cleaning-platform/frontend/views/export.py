"""Trang Xuất dữ liệu: xuất phiên bản hiện tại ra CSV/Excel kèm báo cáo chất lượng."""

import streamlit as st

from components.ui import page_shell

page_shell("Xuất dữ liệu", "Tải dữ liệu đã làm sạch kèm báo cáo chất lượng")

st.info(
    "TODO: hiển thị components.quality_gauge cho điểm chất lượng hiện tại, nút xuất CSV "
    "(GET /api/v1/export/{version_id}/csv) và Excel (GET "
    "/api/v1/export/{version_id}/excel) qua st.download_button."
)
