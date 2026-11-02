"""Trang Tổng quan dữ liệu: kết quả profiling từng cột và điểm chất lượng của phiên bản hiện tại."""

from typing import Any

import pandas as pd
import streamlit as st

from api_client import get_quality
from components.charts import render_missing_ratio_chart, render_type_chart
from components.dataset_context import dataset_context_bar, load_profile
from components.formatting import format_number, format_percent
from components.labels import type_label
from components.navigation import get_page
from components.ui import (
    badge_html,
    data_table,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    stepper,
)
from state import get_token

_EMPTY = "—"
_HIGH_MISSING_RATIO = 0.1  # từ ngưỡng này cột được ghi chú "Thiếu nhiều"


def _column_table(columns: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Cột": c["column_name"],
            "Kiểu": type_label(c["inferred_type"]),
            "Thiếu (%)": c["null_ratio"] * 100,
            "Lưu ý": "Thiếu nhiều" if c["null_ratio"] >= _HIGH_MISSING_RATIO else "",
            "Khác nhau": c["unique_count"],
            "Nhỏ nhất": c["min_value"] or _EMPTY,
            "Lớn nhất": c["max_value"] or _EMPTY,
            "Trung bình": (
                f"{c['mean_value']:.2f}".replace(".", ",")
                if c["mean_value"] is not None
                else _EMPTY
            ),
            "Định dạng": c["detected_format"] or _EMPTY,
            "Giá trị mẫu": ", ".join(str(v) for v in c["sample_values"]),
        }
        for c in columns
    )


def _column_detail(columns: list[dict[str, Any]]) -> None:
    names = [c["column_name"] for c in columns]
    chosen = st.selectbox("Chi tiết một cột", names, key="overview_column")
    column = columns[names.index(chosen)]
    cells = st.columns(3)
    with cells[0]:
        metric_card("Kiểu dữ liệu", type_label(column["inferred_type"]))
    with cells[1]:
        metric_card(
            "Giá trị thiếu",
            f"{format_number(column['null_count'])} ({format_percent(column['null_ratio'])})",
        )
    with cells[2]:
        metric_card("Giá trị khác nhau", format_number(column["unique_count"]))
    if column["sample_values"]:
        samples = " ".join(badge_html(str(v)) for v in column["sample_values"])
        st.markdown(f"**Giá trị mẫu:** {samples}", unsafe_allow_html=True)


page_shell("Tổng quan dữ liệu", "Thống kê từng cột và điểm chất lượng của phiên bản hiện tại")
stepper("overview")
active = dataset_context_bar()
version = active.version

rerun = st.button("Phân tích lại", icon=":material/refresh:", help="Chạy lại phân tích dữ liệu")
profile, error = load_profile(version["id"], force=rerun)
if error is not None:
    error_state(error, key="overview")
    st.stop()
if rerun:
    st.toast("Đã phân tích lại dữ liệu.", icon=":material/check_circle:")

columns = profile["columns"]
if not columns:
    empty_state(
        "table_chart",
        "Chưa có cột nào để phân tích",
        "Dataset không có cột dữ liệu. Hãy tải lên một file khác.",
        cta_label="Tải file khác",
        cta_page="upload",
    )
    st.stop()

quality, _ = safe_call("Đang tính điểm chất lượng…", get_quality, get_token(), version["id"])
average_missing = sum(c["null_ratio"] for c in columns) / len(columns)
score = f"{quality['overall_score']:.1f}".replace(".", ",") + " / 100" if quality else "—"

for cell, (label, value) in zip(
    st.columns(4),
    [
        ("Số dòng", format_number(version["row_count"])),
        ("Số cột", format_number(len(columns))),
        ("Tỉ lệ thiếu trung bình", format_percent(average_missing)),
        ("Điểm chất lượng", score),
    ],
    strict=True,
):
    with cell:
        metric_card(label, value)

tab_stats, tab_charts = st.tabs(["Thống kê cột", "Biểu đồ"])
with tab_stats:
    data_table(
        _column_table(columns),
        column_config={
            "Thiếu (%)": st.column_config.ProgressColumn(
                "Thiếu (%)", min_value=0, max_value=100, format="%.1f%%"
            ),
            "Lưu ý": st.column_config.TextColumn("Lưu ý", width="medium"),
            "Khác nhau": st.column_config.NumberColumn("Khác nhau", format="%d"),
            "Định dạng": st.column_config.TextColumn("Định dạng", width="large"),
        },
        height=min(560, 56 + 36 * len(columns)),
    )
    _column_detail(columns)

with tab_charts:
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Tỉ lệ thiếu theo cột**")
        render_missing_ratio_chart(columns)
    with right:
        st.markdown("**Cơ cấu kiểu dữ liệu**")
        render_type_chart(columns)

if st.button(
    "Tiếp tục: Mapping cột",
    type="primary",
    icon=":material/arrow_forward:",
):
    st.switch_page(get_page("mapping").file)
