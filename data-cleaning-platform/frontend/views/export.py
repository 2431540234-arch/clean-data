"""Trang Xuất dữ liệu: điểm chất lượng và tải phiên bản hiện tại ra CSV hoặc Excel."""

import re
from typing import Any

import streamlit as st

from api_client import export_csv, export_excel, get_quality
from components.dataset_context import dataset_context_bar
from components.formatting import format_bytes, format_number, format_percent
from components.navigation import get_page
from components.quality_gauge import render_quality_gauge, score_label
from components.ui import (
    badge_html,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
    stepper,
)
from state import get_context, get_token, set_context

# Khớp docs/quality_score.md: nhãn và trọng số của 4 tiêu chí thành phần.
_COMPONENTS = [
    ("completeness", "Đầy đủ", 30),
    ("uniqueness", "Không trùng lặp", 20),
    ("validity", "Hợp lệ", 30),
    ("consistency", "Nhất quán", 20),
]
_FORMATS = {
    "csv": {
        "title": "CSV",
        "caption": "Văn bản UTF-8 có BOM, mở đúng tiếng Việt trong Excel.",
        "fetch": export_csv,
        "extension": "csv",
        "mime": "text/csv",
    },
    "excel": {
        "title": "Excel",
        "caption": "Nhiều sheet: dữ liệu đã làm sạch và báo cáo chất lượng.",
        "fetch": export_excel,
        "extension": "xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
}


def _file_name(dataset: dict[str, Any], version: dict[str, Any], extension: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", str(dataset["name"])).strip("_") or "du_lieu"
    return f"{stem}_v{version['version_number']}.{extension}"


def _quality_section(version_id: int) -> None:
    quality, error = safe_call("Đang tính điểm chất lượng…", get_quality, get_token(), version_id)
    if error is not None:
        error_state(error, key="export_quality")
        return
    score = quality["overall_score"]
    label, kind = score_label(score)
    gauge_col, detail_col = st.columns([2, 3])
    with gauge_col:
        render_quality_gauge(score)
        value = f"{score:.1f}".replace(".", ",")
        st.markdown(f"### {value} / 100 &nbsp; {badge_html(label, kind)}", unsafe_allow_html=True)
    with detail_col:
        st.markdown("**Các tiêu chí thành phần**")
        for key, title, weight in _COMPONENTS:
            share = quality.get(key)
            if share is None:
                continue
            st.progress(share, text=f"{title} · {format_percent(share)} (trọng số {weight}%)")


def _export_card(key: str, dataset: dict[str, Any], version: dict[str, Any]) -> None:
    spec = _FORMATS[key]
    store = get_context().setdefault("exports", {})
    ready = store.get(key)
    if ready and ready["version_id"] != version["id"]:
        ready = None  # phiên bản đã đổi: file cũ không còn đúng
    with section(f"Tệp {spec['title']}", caption=spec["caption"]):
        if st.button(
            f"Tạo tệp {spec['title']}",
            key=f"make_{key}",
            icon=":material/draft:",
            use_container_width=True,
        ):
            content, error = safe_call(
                f"Đang tạo tệp {spec['title']}…", spec["fetch"], get_token(), version["id"]
            )
            if error is not None:
                if error.status_code >= 500 or error.status_code == 0:
                    error_state(error, key=f"export_{key}")
                else:
                    st.error(error.detail, icon=":material/error:")
            else:
                store[key] = ready = {"version_id": version["id"], "content": content}
                set_context(exports=store)
        if ready:
            st.download_button(
                f"Tải xuống ({format_bytes(len(ready['content']))})",
                data=ready["content"],
                file_name=_file_name(dataset, version, spec["extension"]),
                mime=spec["mime"],
                key=f"download_{key}",
                icon=":material/download:",
                type="primary",
                use_container_width=True,
            )


page_shell("Xuất dữ liệu", "Tải dữ liệu đã làm sạch kèm báo cáo chất lượng")
stepper("export")
active = dataset_context_bar()
dataset, version = active.dataset, active.version

metric_cols = st.columns(3)
for cell, (label, value) in zip(
    metric_cols,
    [
        ("Phiên bản xuất", f"Phiên bản {version['version_number']}"),
        ("Số dòng", format_number(version["row_count"])),
        ("Số cột", format_number(version["column_count"])),
    ],
    strict=True,
):
    with cell:
        metric_card(label, value)

st.subheader("Điểm chất lượng")
_quality_section(version["id"])

st.subheader("Xuất dữ liệu")
csv_col, excel_col = st.columns(2)
with csv_col:
    _export_card("csv", dataset, version)
with excel_col:
    _export_card("excel", dataset, version)

if version["version_number"] == 1:
    st.info(
        "Bạn đang xuất phiên bản gốc, chưa làm sạch. Hãy áp dụng gợi ý ở bước Gợi ý làm sạch "
        "nếu muốn xuất dữ liệu đã làm sạch.",
        icon=":material/info:",
    )
    if st.button("Đến Gợi ý làm sạch", icon=":material/auto_fix_high:"):
        st.switch_page(get_page("suggestions").file)
