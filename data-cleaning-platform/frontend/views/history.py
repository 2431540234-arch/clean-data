"""Trang Lịch sử phiên bản: xem các version, hoàn tác/làm lại, khôi phục phiên bản cũ.

Hoàn tác/làm lại đi theo cây phiên bản (parent_version_id) và không xóa phiên bản nào.
"""

from typing import Any

import streamlit as st

from api_client import list_dataset_versions, redo_version, restore_version, undo_version
from components.dataset_context import dataset_context_bar
from components.navigation import get_page
from components.ui import empty_state, error_state, page_shell, safe_call
from components.version_timeline import can_redo, can_undo, render_version_timeline
from state import get_context, get_current_user, get_token, set_context, set_flash


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
    set_flash(message.format(n=result["version_number"]))
    st.rerun()


page_shell("Lịch sử phiên bản", "Xem các phiên bản, hoàn tác hoặc khôi phục")
active = dataset_context_bar()
dataset, current = active.dataset, active.version

versions, error = safe_call("Đang tải lịch sử…", list_dataset_versions, get_token(), dataset["id"])
if error is not None:
    error_state(error, key="history")
    st.stop()

undo_col, redo_col, _ = st.columns([2, 2, 5])
if undo_col.button(
    "Hoàn tác",
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

if len(versions) == 1:
    empty_state(
        "history",
        "Chưa có thay đổi nào",
        "Dataset mới chỉ có phiên bản gốc. Áp dụng các gợi ý làm sạch để tạo phiên bản mới.",
        cta_label="Đến Gợi ý làm sạch",
        cta_page="suggestions",
    )

restore_id = render_version_timeline(versions, current["id"], (get_current_user() or {}).get("id"))
if restore_id is not None:
    _change_version(
        "Đang khôi phục…",
        restore_version,
        dataset["id"],
        restore_id,
        message="Đã khôi phục phiên bản {n}.",
    )

if get_context().get("dataset_id") and len(versions) > 1:
    export_col, _ = st.columns([2, 5])
    if export_col.button("Xuất dữ liệu", icon=":material/download:", use_container_width=True):
        st.switch_page(get_page("export").file)
