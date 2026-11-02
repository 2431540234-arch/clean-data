"""Trang chủ: lời chào, dataset đang làm việc và lối tắt tới từng bước của quy trình."""

import streamlit as st

from components.navigation import FLOW_KEYS, PRODUCT_TAGLINE, get_page
from components.ui import empty_state, page_shell, section
from state import get_context, get_current_user

# Mô tả giữ trong một dòng (<= ~28 ký tự) để các thẻ cao đều nhau mà không cần chiều cao cố định.
_STEP_DESCRIPTIONS = {
    "upload": "Tải file CSV/Excel lên.",
    "overview": "Thống kê cột và lỗi dữ liệu.",
    "mapping": "Đổi tên cột về schema chuẩn.",
    "suggestions": "Duyệt gợi ý AI, xem trước.",
    "history": "Hoàn tác, làm lại, khôi phục.",
    "export": "Tải CSV/Excel kèm báo cáo.",
}
_COLUMNS = 3

user = get_current_user() or {}
name = user.get("full_name") or user.get("email") or "bạn"
page_shell(f"Xin chào, {name}", PRODUCT_TAGLINE)

context = get_context()
if context.get("dataset_id"):
    dataset = context.get("dataset_name") or f"Dataset #{context['dataset_id']}"
    project = context.get("project_name") or f"#{context.get('project_id')}"
    with section("Đang làm việc với"):
        st.markdown(f"**{dataset}** · project {project}")
        if st.button("Tiếp tục", icon=":material/arrow_forward:", type="primary"):
            st.switch_page(get_page("overview").file)
else:
    empty_state(
        "upload_file",
        "Chưa có dữ liệu đang làm việc",
        "Tải một file CSV/Excel lên để bắt đầu quy trình làm sạch.",
        cta_label="Tải dữ liệu lên",
        cta_page="upload",
    )

st.subheader("Quy trình làm sạch")
for start in range(0, len(FLOW_KEYS), _COLUMNS):
    for column, key in zip(st.columns(_COLUMNS), FLOW_KEYS[start : start + _COLUMNS], strict=True):
        page = get_page(key)
        with column, st.container(border=True):
            st.markdown(f"**{FLOW_KEYS.index(key) + 1}. :material/{page.icon}: {page.title}**")
            st.caption(_STEP_DESCRIPTIONS[key])
            if st.button("Mở", key=f"home_open_{key}", use_container_width=True):
                st.switch_page(page.file)
