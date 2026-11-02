"""Trang Dashboard: tổng quan các project của người dùng (admin thấy toàn bộ)."""

from typing import Any

import streamlit as st

from api_client import create_project, delete_project, list_projects, update_project
from components.formatting import format_date, format_number
from components.navigation import get_page
from components.ui import (
    badge_html,
    confirm_button,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
)
from state import get_current_user, get_token, set_context, set_flash

_COLUMNS = 3
_MAX_NAME_LENGTH = 255  # khớp ProjectCreate.name(max_length=255)


def _check_name(name: str) -> str | None:
    """Trả thông báo lỗi nếu tên project không hợp lệ, None nếu hợp lệ."""
    if not name.strip():
        return "Vui lòng nhập tên project."
    if len(name.strip()) > _MAX_NAME_LENGTH:
        return f"Tên project tối đa {_MAX_NAME_LENGTH} ký tự."
    return None


def _run_action(label: str, func: Any, *args: Any) -> tuple[bool, Any]:
    """Gọi API với spinner; lỗi hiện ngay tại chỗ. Trả (thành công, kết quả)."""
    result, error = safe_call(label, func, *args)
    if error is not None:
        st.error(error.detail, icon=":material/error:")
        return False, None
    return True, result


@st.dialog("Tạo project mới")
def _create_dialog() -> None:
    name = st.text_input("Tên project", placeholder="Ví dụ: Khách hàng 2026", max_chars=255)
    left, right = st.columns(2)
    if left.button("Hủy", use_container_width=True):
        st.rerun()
    if right.button("Tạo project", type="primary", use_container_width=True):
        problem = _check_name(name)
        if problem:
            st.error(problem, icon=":material/error:")
            return
        ok, project = _run_action("Đang tạo project…", create_project, get_token(), name.strip())
        if ok:
            set_flash(f"Đã tạo project “{project['name']}”.")
            st.rerun()


def _open_project(project: dict[str, Any]) -> None:
    """Chọn project làm ngữ cảnh làm việc rồi chuyển tới bước Tải lên."""
    set_context(
        project_id=project["id"],
        project_name=project["name"],
        dataset_id=None,
        dataset_name=None,
        version_id=None,
    )
    st.switch_page(get_page("upload").file)


def _project_card(project: dict[str, Any], current_user_id: int | None) -> None:
    pid = project["id"]
    with st.container(border=True):
        st.markdown(f"**{project['name']}**")
        owner = (
            badge_html("Của bạn", "primary")
            if project["owner_id"] == current_user_id
            else badge_html(f"Người dùng #{project['owner_id']}", "neutral")
        )
        st.markdown(owner, unsafe_allow_html=True)
        st.caption(f"Tạo ngày {format_date(project['created_at'])}")

        if st.button("Mở", key=f"open_{pid}", type="primary", use_container_width=True):
            _open_project(project)
        with st.popover("Thêm", icon=":material/more_horiz:", use_container_width=True):
            new_name = st.text_input("Tên mới", value=project["name"], key=f"name_{pid}")
            if st.button("Lưu tên", key=f"rename_{pid}", use_container_width=True):
                problem = _check_name(new_name)
                if problem:
                    st.error(problem, icon=":material/error:")
                else:
                    ok, _ = _run_action(
                        "Đang lưu…", update_project, get_token(), pid, new_name.strip()
                    )
                    if ok:
                        set_flash("Đã đổi tên project.")
                        st.rerun()
            st.divider()
            confirmed = confirm_button(
                "Xóa project",
                key=f"delete_{pid}",
                icon=":material/delete:",
                title="Xóa project?",
                message=(
                    f"Project “{project['name']}” và toàn bộ dataset bên trong sẽ bị xóa. "
                    "Không thể hoàn tác."
                ),
                confirm_label="Xóa",
                warning=True,
            )
            if confirmed:
                ok, _ = _run_action("Đang xóa…", delete_project, get_token(), pid)
                if ok:
                    set_flash("Đã xóa project.")
                    st.rerun()


page_shell("Dashboard", "Các project làm sạch dữ liệu của bạn")

token = get_token()
user = get_current_user() or {}

if st.button("Tạo project", icon=":material/add:", type="primary"):
    _create_dialog()

projects, error = safe_call("Đang tải project…", list_projects, token)
if error is not None:
    error_state(error, key="dashboard")
    st.stop()

projects = sorted(projects, key=lambda p: p["created_at"], reverse=True)

if not projects:
    if empty_state(
        "folder_open",
        "Chưa có project nào",
        "Project gom các dataset cùng mục đích. Hãy tạo project đầu tiên để bắt đầu.",
        cta_label="Tạo project đầu tiên",
    ):
        _create_dialog()
    st.stop()

_KPI_COLUMNS = 4  # số thẻ KPI tối đa mỗi hàng; thêm thẻ mới chỉ cần thêm vào _kpi_tiles


def _kpi_tiles(projects: list[dict[str, Any]], user: dict[str, Any]) -> list[tuple[str, str]]:
    """Các thẻ KPI (nhãn, giá trị) tính từ dữ liệu có thật của ProjectOut.

    TODO(backend): thêm "Số dataset" và "Điểm chất lượng TB" khi backend có dữ liệu
    (docs/BACKEND_TODO.md, mục 2 #1 và #6): chỉ cần thêm một dòng vào danh sách này.
    """
    tiles = [
        ("Số project", format_number(len(projects))),
        ("Tạo gần nhất", format_date(projects[0]["created_at"])),
    ]
    if user.get("role") == "admin":
        tiles.append(("Số chủ sở hữu", format_number(len({p["owner_id"] for p in projects}))))
    return tiles


tiles = _kpi_tiles(projects, user)
for start in range(0, len(tiles), _KPI_COLUMNS):
    for column, (label, value) in zip(
        st.columns(_KPI_COLUMNS), tiles[start : start + _KPI_COLUMNS], strict=False
    ):
        with column:
            metric_card(label, value)

st.subheader("Project")
for start in range(0, len(projects), _COLUMNS):
    for column, project in zip(
        st.columns(_COLUMNS), projects[start : start + _COLUMNS], strict=False
    ):
        with column:
            _project_card(project, user.get("id"))
