"""Trang Lịch sử phiên bản: xem các version, undo/redo, khôi phục phiên bản cũ."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Lịch sử phiên bản", page_icon="🕒")
init_state()
require_login()

st.title("🕒 Lịch sử phiên bản")
st.info(
    "TODO: gọi GET /api/v1/datasets/{id}/versions, hiển thị bằng "
    "components.version_timeline; thêm nút Undo/Redo gọi "
    "POST /api/v1/versions/{dataset_id}/undo|redo."
)
