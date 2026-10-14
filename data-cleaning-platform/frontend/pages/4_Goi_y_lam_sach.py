"""Trang Gợi ý làm sạch: xem gợi ý AI/rule, duyệt từng gợi ý, xem preview trước khi áp dụng."""

import streamlit as st

from components.auth_guard import require_login
from state import init_state

st.set_page_config(page_title="Gợi ý làm sạch", page_icon="✨")
init_state()
require_login()

st.title("✨ Gợi ý làm sạch dữ liệu")
st.info(
    "TODO: gọi POST /api/v1/suggestions/generate, hiển thị từng gợi ý bằng "
    "components.suggestion_card; khi người dùng chấp nhận, gọi POST /api/v1/preview "
    "để xem trước (components.diff_table), rồi mới gọi POST /api/v1/versions/{id}/apply."
)
