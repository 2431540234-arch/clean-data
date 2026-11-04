"""Trang Xuất dữ liệu: điểm chất lượng và tải một phiên bản ra CSV hoặc Excel."""

import re
from typing import Any

import pandas as pd
import streamlit as st

from api_client import (
    APIError,
    audit_me,
    export_csv,
    export_excel,
    get_quality,
    list_dataset_versions,
)
from components.dataset_context import dataset_context_bar
from components.formatting import format_bytes, format_datetime, format_number, format_percent
from components.navigation import get_page
from components.quality_gauge import render_quality_gauge, score_label
from components.ui import (
    badge_html,
    data_table,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
)
from state import get_context, get_token, set_context

# Khớp docs/quality_score.md: nhãn và trọng số của 4 tiêu chí thành phần.
_COMPONENTS = [
    ("completeness", "Đầy đủ", 30),
    ("uniqueness", "Không trùng lặp", 20),
    ("validity", "Hợp lệ", 30),
    ("consistency", "Nhất quán", 20),
]
# Các sheet của file Excel do backend dựng (backend/app/api/v1/export.py, _build_excel).
_EXCEL_SHEETS = (
    ("Dữ liệu", "dữ liệu của phiên bản đã chọn"),
    ("Báo cáo chất lượng", "điểm tổng và bốn tiêu chí"),
    ("Lỗi đã phát hiện", "cột, loại lỗi, mức độ, số dòng, mô tả"),
)
_FORMATS = {
    "csv": {
        "title": "CSV",
        "badge": "UTF-8 có BOM · mở đúng tiếng Việt trong Excel",
        "fetch": export_csv,
        "extension": "csv",
        "mime": "text/csv",
    },
    "excel": {
        "title": "Excel",
        "badge": f"{len(_EXCEL_SHEETS)} sheet",
        "fetch": export_excel,
        "extension": "xlsx",
        "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    },
}
_HISTORY_LIMIT = 10


def _file_name(dataset: dict[str, Any], version: dict[str, Any], extension: str) -> str:
    stem = re.sub(r"[^\w.-]+", "_", str(dataset["name"])).strip("_") or "du_lieu"
    return f"{stem}_v{version['version_number']}.{extension}"


def _score_text(score: float) -> str:
    return f"{score:.1f}".replace(".", ",")


def _quality_of(version_id: int) -> dict[str, Any] | None:
    try:
        return get_quality(get_token(), version_id)
    except APIError:
        return None


def _quality_section(version: dict[str, Any], root: dict[str, Any] | None) -> None:
    """Thẻ "Điểm chất lượng": đồng hồ, bốn tiêu chí, công thức và so sánh với bản gốc."""
    with section("Điểm chất lượng"):
        quality, error = safe_call(
            "Đang tính điểm chất lượng…", get_quality, get_token(), version["id"]
        )
        if error is not None:
            error_state(error, key="export_quality")
            return
        score = quality["overall_score"]
        label, kind = score_label(score)
        render_quality_gauge(score)
        st.markdown(
            f"### {_score_text(score)} / 100 &nbsp; {badge_html(label, kind)}",
            unsafe_allow_html=True,
        )
        for key, title, weight in _COMPONENTS:
            share = quality.get(key)
            if share is None:
                continue
            st.progress(share, text=f"{title} · {format_percent(share)} (trọng số {weight}%)")
        st.info(
            "Điểm tổng = 0,3 × Đầy đủ + 0,2 × Không trùng lặp + 0,3 × Hợp lệ "
            "+ 0,2 × Nhất quán, quy về thang 100.",
            icon=":material/functions:",
        )
        if root is not None and root["id"] != version["id"]:
            original = _quality_of(root["id"])
            if original is not None:
                delta = score - original["overall_score"]
                left, right = st.columns(2)
                with left:
                    metric_card(
                        f"Bản gốc (v{root['version_number']})",
                        _score_text(original["overall_score"]),
                    )
                with right:
                    metric_card(
                        f"Phiên bản xuất (v{version['version_number']})",
                        _score_text(score),
                        delta=(f"{delta:+.1f}".replace(".", ",") + " điểm") if delta else None,
                        delta_color="normal",
                    )


def _export_card(key: str, dataset: dict[str, Any], version: dict[str, Any]) -> None:
    spec = _FORMATS[key]
    store = get_context().setdefault("exports", {})
    ready = store.get(key)
    if ready and ready["version_id"] != version["id"]:
        ready = None  # phiên bản đã đổi: file cũ không còn đúng
    with section(f"Tệp {spec['title']}"):
        st.caption(spec["badge"])
        file_name = st.text_input(
            "Tên file",
            value=_file_name(dataset, version, spec["extension"]),
            key=f"export_name_{key}_{version['id']}",
        )
        if key == "csv":
            st.caption(
                "Ô bắt đầu bằng = + - @ được thêm dấu ' phía trước "
                "để Excel không hiểu là công thức."
            )
        else:
            for sheet, description in _EXCEL_SHEETS:
                st.markdown(f"- Sheet “{sheet}”: {description}")
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
                file_name=file_name.strip() or _file_name(dataset, version, spec["extension"]),
                mime=spec["mime"],
                key=f"download_{key}",
                icon=":material/download:",
                type="primary",
                use_container_width=True,
            )


def _history_section(dataset_id: int) -> None:
    """Lịch sử xuất của dataset, lấy từ nhật ký hoạt động (action "dataset.export")."""
    with section("Lịch sử xuất", caption="Các lần xuất gần đây của dataset này."):
        entries, error = safe_call("Đang tải lịch sử xuất…", audit_me, get_token())
        if error is not None:
            st.caption(f"Chưa lấy được lịch sử xuất: {error.detail}")
            return
        exported = [
            e
            for e in entries
            if e["action"] == "dataset.export" and e["entity_id"] == dataset_id and e["new_value"]
        ][:_HISTORY_LIMIT]
        if not exported:
            st.caption("Chưa có lần xuất nào.")
            return
        data_table(
            pd.DataFrame(
                {
                    "Định dạng": _FORMATS.get(e["new_value"].get("format"), {}).get(
                        "title", str(e["new_value"].get("format"))
                    ),
                    "Phiên bản": f"v{e['new_value'].get('version_number', '?')}",
                    "Dung lượng": format_bytes(int(e["new_value"].get("bytes") or 0)),
                    "Thời gian": format_datetime(e["created_at"]),
                }
                for e in exported
            ),
            height=min(400, 56 + 36 * len(exported)),
        )


page_shell("Xuất dữ liệu", "Kiểm tra điểm chất lượng rồi tải dữ liệu sạch về máy")
active = dataset_context_bar()
dataset, current = active.dataset, active.version

versions, error = safe_call(
    "Đang tải danh sách phiên bản…", list_dataset_versions, get_token(), dataset["id"]
)
if error is not None:
    error_state(error, key="export_versions")
    st.stop()
by_id = {v["id"]: v for v in versions}
root = next((v for v in versions if v["parent_version_id"] is None), None)

_, picker_col = st.columns([3, 1.6])
ordered = sorted(versions, key=lambda v: v["version_number"], reverse=True)
if (
    st.session_state.get("export_version") not in by_id
    or st.session_state.get("export_version_dataset") != dataset["id"]
):
    st.session_state["export_version"] = current["id"]
    st.session_state["export_version_dataset"] = dataset["id"]
version_id = picker_col.selectbox(
    "Phiên bản xuất",
    [v["id"] for v in ordered],
    format_func=lambda vid: f"v{by_id[vid]['version_number']}"
    + (" · Hiện tại" if vid == current["id"] else ""),
    key="export_version",
)
version = by_id[version_id]
picker_col.caption(
    f"{format_number(version['row_count'])} dòng × {format_number(version['column_count'])} cột"
)

quality_col, files_col = st.columns([1, 1.2], gap="large")
with quality_col:
    _quality_section(version, root)
with files_col:
    _export_card("csv", dataset, version)
    _export_card("excel", dataset, version)

_history_section(dataset["id"])

if version["version_number"] == 1:
    st.info(
        "Bạn đang xuất phiên bản gốc, chưa làm sạch. Hãy áp dụng gợi ý ở bước Gợi ý làm sạch "
        "nếu muốn xuất dữ liệu đã làm sạch.",
        icon=":material/info:",
    )
    if st.button("Đến Gợi ý làm sạch", icon=":material/auto_fix_high:"):
        st.switch_page(get_page("suggestions").file)
