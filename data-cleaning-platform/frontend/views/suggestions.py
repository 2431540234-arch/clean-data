"""Trang Gợi ý làm sạch: xem gợi ý AI/rule, duyệt từng gợi ý, xem preview trước khi áp dụng."""

import streamlit as st

from components.ui import page_shell

page_shell("Gợi ý làm sạch", "Duyệt gợi ý của AI và xem trước khi áp dụng")

st.info(
    "TODO: gọi POST /api/v1/suggestions/generate, hiển thị từng gợi ý bằng "
    "components.suggestion_card; khi người dùng chấp nhận, gọi POST /api/v1/preview để "
    "xem trước (components.diff_table), rồi mới gọi POST /api/v1/versions/{id}/apply."
)
