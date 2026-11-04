"""Trang Lịch sử phiên bản: xem các version, hoàn tác/làm lại, khôi phục phiên bản cũ.

Hoàn tác/làm lại đi theo cây phiên bản (parent_version_id) và không xóa phiên bản nào.
"""

from typing import Any

import streamlit as st

from api_client import (
    APIError,
    get_quality,
    list_dataset_versions,
    redo_version,
    restore_version,
    undo_version,
)
from components.dataset_context import dataset_context_bar
from components.formatting import format_datetime, format_number
from components.navigation import get_page
from components.ui import empty_state, error_state, metric_card, page_shell, safe_call, section
from components.version_timeline import can_redo, can_undo, render_version_timeline
from state import get_current_user, get_token, set_context, set_flash

_SELECTED_KEY = "history_selected_version"


def _change_version(label: str, func: Any, *args: Any, message: str) -> None:
    """Gọi undo/redo/restore; thành công thì báo, bỏ kết quả xem trước cũ và nạp lại trang."""
    result, error = safe_call(label, func, get_token(), *args)
    if error is not None:
        if error.status_code >= 500 or error.status_code == 0:
            error_state(error, key="history_action")
        else:
            st.error(error.detail, icon=":material/error:")
        return
    set_context(preview=None, last_applied=None, no_issues_version=None)
    st.session_state.pop(_SELECTED_KEY, None)
    set_flash(message.format(n=result["version_number"]))
    st.rerun()


def _score(version_id: int) -> float | None:
    """Điểm chất lượng của một phiên bản; None nếu chưa có báo cáo hoặc không lấy được."""
    try:
        return get_quality(get_token(), version_id)["overall_score"]
    except APIError:
        return None


def _score_text(score: float | None) -> str:
    return f"{score:.1f}".replace(".", ",") if score is not None else "—"


def _detail(version: dict[str, Any], parent: dict[str, Any] | None, current_id: int) -> None:
    """Chi tiết phiên bản đang xem: số dòng/cột, điểm chất lượng và mô tả thay đổi."""
    number = version["version_number"]
    caption = (
        f"Tạo từ phiên bản {parent['version_number']}" if parent else "Bản gốc khi tải lên"
    ) + f" · {format_datetime(version['created_at'])}"
    with section(f"Chi tiết phiên bản {number}", caption=caption):
        score = _score(version["id"])
        parent_score = _score(parent["id"]) if parent else None
        rows_delta = cols_delta = score_delta = None
        if parent is not None:
            tail = f"so v{parent['version_number']}"
            # Dấu "-" ASCII để Streamlit nhận là giá trị giảm (dấu trừ Unicode bị coi là tăng).
            if version["row_count"] != parent["row_count"]:
                rows_delta = f"{version['row_count'] - parent['row_count']:+d} {tail}"
            if version["column_count"] != parent["column_count"]:
                cols_delta = f"{version['column_count'] - parent['column_count']:+d} {tail}"
            if score is not None and parent_score is not None and score != parent_score:
                score_delta = f"{(score - parent_score):+.1f}".replace(".", ",") + f" {tail}"
        with st.container(key="dc-version-kpis"):
            for cell, (label, value, delta, color) in zip(
                st.columns(3),
                [
                    ("Số dòng", format_number(version["row_count"]), rows_delta, "off"),
                    ("Số cột", format_number(version["column_count"]), cols_delta, "off"),
                    ("Điểm chất lượng", _score_text(score), score_delta, "normal"),
                ],
                strict=True,
            ):
                with cell:
                    metric_card(label, value, delta=delta, delta_color=color)
        st.markdown("**Mô tả thay đổi**")
        st.write(version.get("change_summary") or "—")
        if version["id"] == current_id:
            st.caption("Đây là phiên bản hiện tại: làm sạch và xuất dữ liệu dùng phiên bản này.")


page_shell("Lịch sử phiên bản", "Mỗi lần áp dụng tạo phiên bản mới. Không phiên bản nào bị xóa.")
active = dataset_context_bar()
dataset, current = active.dataset, active.version

versions, error = safe_call("Đang tải lịch sử…", list_dataset_versions, get_token(), dataset["id"])
if error is not None:
    error_state(error, key="history")
    st.stop()

by_id = {v["id"]: v for v in versions}
current_row = by_id[current["id"]]
parent_of_current = by_id.get(current_row["parent_version_id"])
_, undo_col, redo_col, next_col = st.columns([2, 2.2, 1.4, 2.4])
if undo_col.button(
    "Hoàn tác" + (f" (về v{parent_of_current['version_number']})" if parent_of_current else ""),
    icon=":material/undo:",
    disabled=not can_undo(versions, current["id"]),
    use_container_width=True,
    help="Quay lại phiên bản trước của phiên bản hiện tại",
):
    _change_version(
        "Đang hoàn tác…", undo_version, dataset["id"], message="Đã quay lại phiên bản {n}."
    )
if redo_col.button(
    "Làm lại",
    icon=":material/redo:",
    disabled=not can_redo(versions, current["id"]),
    use_container_width=True,
    help="Tiến tới phiên bản kế tiếp sau khi đã hoàn tác",
):
    _change_version(
        "Đang làm lại…", redo_version, dataset["id"], message="Đã chuyển tới phiên bản {n}."
    )
if next_col.button(
    "Tiếp tục: Xuất dữ liệu",
    type="primary",
    icon=":material/arrow_forward:",
    use_container_width=True,
):
    st.switch_page(get_page("export").file)

if len(versions) == 1:
    empty_state(
        "history",
        "Chưa có thay đổi nào",
        "Dataset mới chỉ có phiên bản gốc. Áp dụng các gợi ý làm sạch để tạo phiên bản mới.",
        cta_label="Đến Gợi ý làm sạch",
        cta_page="suggestions",
    )

if st.session_state.get(_SELECTED_KEY) not in by_id:
    st.session_state[_SELECTED_KEY] = current["id"]
selected = by_id[st.session_state[_SELECTED_KEY]]

timeline_col, detail_col = st.columns([1, 1], gap="large")
with timeline_col, section("Dòng thời gian", caption=f"{len(versions)} phiên bản"):
    restore_id, view_id = render_version_timeline(
        versions,
        current["id"],
        (get_current_user() or {}).get("id"),
        selected["id"],
    )
with detail_col:
    _detail(selected, by_id.get(selected["parent_version_id"]), current["id"])

if view_id is not None:
    st.session_state[_SELECTED_KEY] = view_id
    st.rerun()
if restore_id is not None:
    _change_version(
        "Đang khôi phục…",
        restore_version,
        dataset["id"],
        restore_id,
        message="Đã khôi phục phiên bản {n}.",
    )
