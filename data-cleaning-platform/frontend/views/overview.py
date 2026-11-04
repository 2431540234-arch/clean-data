"""Trang Tổng quan dữ liệu: kết quả profiling từng cột và điểm chất lượng của phiên bản hiện tại."""

from typing import Any

import pandas as pd
import streamlit as st

from api_client import get_issues, get_quality, get_rows
from components.charts import (
    render_distribution_chart,
    render_issue_chart,
    render_missing_ratio_chart,
    render_type_chart,
)
from components.dataset_context import dataset_context_bar, load_profile
from components.formatting import format_number, format_percent
from components.labels import SEVERITY_KIND, issue_type_label, severity_label, type_label
from components.navigation import get_page
from components.ui import (
    badge_html,
    data_table,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
)
from state import get_token

_EMPTY = "—"
# Tiêu chí điểm chất lượng của backend (services/quality.py): khóa, nhãn, trọng số %
_CRITERIA = (
    ("completeness", "Đầy đủ", 30),
    ("uniqueness", "Không trùng lặp", 20),
    ("validity", "Hợp lệ", 30),
    ("consistency", "Nhất quán", 20),
)
_HIGH_MISSING_RATIO = 0.1  # từ ngưỡng này cột được ghi chú "Thiếu nhiều"
_DISTRIBUTION_ROWS = 1000  # số dòng đầu dùng để vẽ phân bố giá trị của một cột


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


def _issue_table(issues: list[dict[str, Any]]) -> None:
    """Danh sách lỗi đã phát hiện: mức độ, cột, loại, số dòng, ví dụ và mô tả."""
    data_table(
        pd.DataFrame(
            {
                "Mức độ": severity_label(i["severity"]),
                "Cột": i["column_name"] or "(cả bảng)",
                "Loại lỗi": issue_type_label(i["issue_type"]),
                "Số dòng": i["affected_count"],
                "Ví dụ": ", ".join(repr(x) for x in i["examples"]),
                "Mô tả": i["message"],
            }
            for i in issues
        ),
        column_config={
            "Số dòng": st.column_config.NumberColumn("Số dòng", format="%d"),
            "Mô tả": st.column_config.TextColumn("Mô tả", width="large"),
        },
        height=min(560, 56 + 36 * len(issues)),
    )


def _severity_counts(issues: list[dict[str, Any]]) -> str:
    """Ví dụ "4 cao · 6 trung bình · 3 thấp" (bỏ mức không có lỗi)."""
    parts = [
        f"{count} {severity_label(level).lower()}"
        for level in ("high", "medium", "low")
        if (count := sum(1 for i in issues if i["severity"] == level))
    ]
    return " · ".join(parts)


def _issues_section(issues: list[dict[str, Any]] | None, error_detail: str | None) -> None:
    """Tab "Lỗi đã phát hiện"."""
    if issues is None:
        st.warning(f"Chưa lấy được danh sách lỗi: {error_detail}", icon=":material/warning:")
        return
    if not issues:
        st.success("Không phát hiện lỗi nào trong dữ liệu.", icon=":material/check_circle:")
        return
    summary = " ".join(
        badge_html(
            f"{severity_label(level)}: {sum(1 for i in issues if i['severity'] == level)}",
            SEVERITY_KIND[level],
        )
        for level in ("high", "medium", "low")
        if any(i["severity"] == level for i in issues)
    )
    st.markdown(f"**{len(issues)} nhóm lỗi** · {summary}", unsafe_allow_html=True)
    _issue_table(issues)


def _criteria_section(quality: dict[str, Any]) -> None:
    """Điểm chất lượng theo bốn tiêu chí (0..1) kèm trọng số; điểm tổng = Σ trọng số × tiêu chí."""
    with section(
        "Điểm chất lượng theo tiêu chí",
        caption="Điểm tổng (0–100) là trung bình có trọng số của bốn tiêu chí (mỗi tiêu chí 0–1).",
    ):
        for cell, (key, label, weight) in zip(st.columns(4), _CRITERIA, strict=True):
            value = quality.get(key)
            with cell:
                st.markdown(f"{label} ({weight}%)")
                if value is None:
                    st.caption("Chưa có dữ liệu")
                    continue
                st.progress(min(max(float(value), 0.0), 1.0), text=f"{value:.2f}".replace(".", ","))


def _distribution(dataset_id: int, version_id: int, columns: list[dict[str, Any]]) -> None:
    """Phân bố giá trị của một cột, vẽ từ các dòng đầu của phiên bản (GET .../rows)."""
    names = [c["column_name"] for c in columns]
    chosen = st.selectbox("Phân bố giá trị của cột", names, key="overview_distribution_column")
    page, error = safe_call(
        "Đang tải dữ liệu…", get_rows, get_token(), dataset_id, version_id, 0, _DISTRIBUTION_ROWS
    )
    if error is not None:
        st.warning(f"Chưa lấy được dữ liệu để vẽ: {error.detail}", icon=":material/warning:")
        return
    render_distribution_chart([r["values"].get(chosen) for r in page["rows"]], chosen)
    if page["total"] > len(page["rows"]):
        shown, total = format_number(len(page["rows"])), format_number(page["total"])
        st.caption(f"Vẽ từ {shown} dòng đầu trong {total} dòng.")


page_shell("Tổng quan dữ liệu", "Thống kê từng cột và điểm chất lượng của phiên bản hiện tại")
active = dataset_context_bar()
version = active.version

_, rerun_col, next_col = st.columns([5, 1.6, 2.6])
rerun = rerun_col.button(
    "Phân tích lại",
    icon=":material/refresh:",
    help="Chạy lại phân tích dữ liệu",
    use_container_width=True,
)
if next_col.button(
    "Tiếp tục: Mapping cột",
    type="primary",
    icon=":material/arrow_forward:",
    use_container_width=True,
):
    st.switch_page(get_page("mapping").file)
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
issues, issues_error = safe_call(
    "Đang tải danh sách lỗi…", get_issues, get_token(), version["id"]
)
average_missing = sum(c["null_ratio"] for c in columns) / len(columns)
worst = max(columns, key=lambda c: c["null_ratio"])
score = f"{quality['overall_score']:.1f}".replace(".", ",") + " / 100" if quality else "—"

kpis: list[tuple[str, str, str | None]] = [
    ("Số dòng", format_number(version["row_count"]), f"Phiên bản {version['version_number']}"),
    (
        "Số cột",
        format_number(len(columns)),
        f"{sum(1 for c in columns if c['null_count'])} cột có ô thiếu",
    ),
    (
        "Tỉ lệ thiếu trung bình",
        format_percent(average_missing),
        (
            f"Cao nhất: {worst['column_name']} ({format_percent(worst['null_ratio'])})"
            if worst["null_ratio"] > 0
            else "Không có ô thiếu"
        ),
    ),
]
if issues is not None:
    kpis.append(("Nhóm lỗi phát hiện", format_number(len(issues)), _severity_counts(issues)))
kpis.append(("Điểm chất lượng", score, "Trên thang 100"))
for cell, (label, value, note) in zip(st.columns(len(kpis)), kpis, strict=True):
    with cell:
        metric_card(label, value, note=note)

if quality:
    _criteria_section(quality)

tab_stats, tab_issues, tab_charts = st.tabs(["Thống kê cột", "Lỗi đã phát hiện", "Biểu đồ"])
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

with tab_issues:
    _issues_section(issues, issues_error.detail if issues_error else None)

with tab_charts:
    left, right = st.columns([3, 2])
    with left:
        st.markdown("**Tỉ lệ thiếu theo cột**")
        render_missing_ratio_chart(columns)
    with right:
        st.markdown("**Cơ cấu kiểu dữ liệu**")
        render_type_chart(columns)
    if issues:
        st.markdown("**Lỗi theo mức độ nghiêm trọng**")
        render_issue_chart(issues)
    _distribution(active.dataset["id"], version["id"], columns)
