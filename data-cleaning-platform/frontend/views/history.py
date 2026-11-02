"""Trang Lịch sử phiên bản: xem các version, undo/redo, khôi phục phiên bản cũ."""

import streamlit as st

from components.ui import page_shell

page_shell("Lịch sử phiên bản", "Xem các phiên bản, hoàn tác hoặc khôi phục")

st.info(
    "TODO: gọi GET /api/v1/datasets/{id}/versions, hiển thị bằng "
    "components.version_timeline; thêm nút Undo/Redo gọi POST "
    "/api/v1/versions/{dataset_id}/undo|redo."
)
