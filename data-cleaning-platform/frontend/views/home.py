"""Trang chủ: lời chào, dataset đang làm việc và lối tắt tới từng bước của quy trình."""

import pandas as pd
import streamlit as st

from api_client import audit_me
from components.dataset_summary import project_dataset_summaries
from components.formatting import format_datetime, format_number
from components.labels import action_label
from components.navigation import FLOW_KEYS, PRODUCT_TAGLINE, get_page
from components.ui import data_table, empty_state, error_state, page_shell, safe_call, section
from state import get_context, get_current_user, get_token

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

project_id = context.get("project_id")
if project_id:
    summaries, error = project_dataset_summaries(get_token(), project_id)
    if error is not None:
        error_state(error, key="home_datasets")
    elif summaries:
        with section("Dataset gần đây", caption="Trong project đang chọn"):
            rows = [
                {
                    "Tên file": item["dataset"]["original_filename"],
                    "Phiên bản": f"v{item['version']['version_number']}",
                    "Kích thước": (
                        f"{format_number(item['version']['row_count'])} dòng · "
                        f"{format_number(item['version']['column_count'])} cột"
                    ),
                    "Điểm chất lượng": (
                        f"{item['quality']['overall_score']:.1f}".replace(".", ",") + " / 100"
                    ),
                }
                for item in summaries
            ]
            data_table(pd.DataFrame(rows), height=min(420, 56 + 36 * len(rows)))
    else:
        with section("Dataset gần đây"):
            st.caption("Project đang chọn chưa có dataset.")
else:
    with section("Dataset gần đây"):
        st.caption("Chọn project ở thanh trên để xem các dataset.")

logs, error = safe_call("Đang tải hoạt động gần đây…", audit_me, get_token())
if error is not None:
    error_state(error, key="home_activity")
elif logs:
    with section("Hoạt động gần đây"):
        rows = [
            {
                "Thời gian": format_datetime(log["created_at"]),
                "Hành động": action_label(log["action"]),
            }
            for log in logs[:5]
        ]
        data_table(pd.DataFrame(rows), height=min(260, 56 + 36 * len(rows)))
else:
    with section("Hoạt động gần đây"):
        st.caption("Chưa có hoạt động nào.")

st.subheader("Quy trình làm sạch")
for start in range(0, len(FLOW_KEYS), _COLUMNS):
    for column, key in zip(st.columns(_COLUMNS), FLOW_KEYS[start : start + _COLUMNS], strict=True):
        page = get_page(key)
        with column, st.container(border=True):
            st.markdown(f"**{FLOW_KEYS.index(key) + 1}. :material/{page.icon}: {page.title}**")
            st.caption(_STEP_DESCRIPTIONS[key])
            if st.button("Mở", key=f"home_open_{key}", use_container_width=True):
                st.switch_page(page.file)
