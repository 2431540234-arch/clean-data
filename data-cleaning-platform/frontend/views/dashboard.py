"""Trang Dashboard: tổng quan các project của người dùng (admin thấy toàn bộ)."""

from typing import Any

import streamlit as st

from api_client import create_project, delete_project, list_projects, update_project
from components.dataset_summary import project_dataset_summaries
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
    section,
)
from state import get_context, get_current_user, get_token, set_context, set_flash

_COLUMNS = 3
_MAX_NAME_LENGTH = 255  # khớp ProjectCreate.name(max_length=255)
_RECENT_PROJECT_COUNT = 5


def _check_name(name: str) -> str | None:
    """Trả thông báo lỗi nếu tên project không hợp lệ, None nếu hợp lệ."""
    if not name.strip():
        return "Vui lòng nhập tên dự án."
    if len(name.strip()) > _MAX_NAME_LENGTH:
        return f"Tên dự án tối đa {_MAX_NAME_LENGTH} ký tự."
    return None


def _run_action(label: str, func: Any, *args: Any) -> tuple[bool, Any]:
    """Gọi API với spinner; lỗi hiện ngay tại chỗ. Trả (thành công, kết quả)."""
    result, error = safe_call(label, func, *args)
    if error is not None:
        st.error(error.detail, icon=":material/error:")
        return False, None
    return True, result


@st.dialog("Tạo dự án mới")
def _create_dialog() -> None:
    name = st.text_input("Tên dự án", placeholder="Ví dụ: Khách hàng 2026", max_chars=255)
    left, right = st.columns(2)
    if left.button("Hủy", use_container_width=True):
        st.rerun()
    if right.button("Tạo dự án", type="primary", use_container_width=True):
        problem = _check_name(name)
        if problem:
            st.error(problem, icon=":material/error:")
            return
        ok, project = _run_action("Đang tạo project…", create_project, get_token(), name.strip())
        if ok:
            set_flash(f"Đã tạo dự án “{project['name']}”.")
            _open_project(project)  # dự án vừa tạo thành ngữ cảnh để tải dữ liệu vào đúng chỗ


def _open_project(project: dict[str, Any], *, to_upload: bool = False) -> None:
    """Chọn project làm ngữ cảnh để nạp danh sách dataset bên dưới."""
    set_context(
        project_id=project["id"],
        project_name=project["name"],
        dataset_id=None,
        dataset_name=None,
        version_id=None,
        upload_result=None,
        rule_queue=[],
        rule_queue_version_id=None,
        preview=None,
        pending_steps=None,
        pending_version_id=None,
        last_applied=None,
        mapping=None,
    )
    if to_upload:
        st.switch_page(get_page("upload").file)
    else:
        st.rerun()


def _open_dataset(project: dict[str, Any], summary: dict[str, Any]) -> None:
    dataset = summary["dataset"]
    version = summary["version"]
    set_context(
        project_id=project["id"],
        project_name=project["name"],
        dataset_id=dataset["id"],
        dataset_name=dataset["original_filename"],
        version_id=version["id"],
        upload_result=None,
        rule_queue=[],
        rule_queue_version_id=None,
        preview=None,
        pending_steps=None,
        pending_version_id=None,
        last_applied=None,
        mapping=None,
    )
    st.switch_page(get_page("overview").file)


def _project_card(
    project: dict[str, Any], current_user_id: int | None, selected: bool = False
) -> None:
    pid = project["id"]
    with st.container(border=True):
        st.markdown(f"**{project['name']}**")
        if selected:
            st.markdown(badge_html("Đang chọn", "primary"), unsafe_allow_html=True)
        owner = (
            badge_html("Của bạn", "primary")
            if project["owner_id"] == current_user_id
            else badge_html(f"Người dùng #{project['owner_id']}", "neutral")
        )
        st.markdown(owner, unsafe_allow_html=True)
        st.caption(f"Tạo ngày {format_date(project['created_at'])}")
        if project.get("dataset_count") is not None:
            summary = f"{format_number(project['dataset_count'])} dataset"
            if project.get("average_quality_score") is not None:
                score = f"{project['average_quality_score']:.1f}".replace(".", ",")
                summary += f" · Điểm chất lượng {score}"
            st.caption(summary)

        open_col, edit_col, delete_col = st.columns(3)
        if open_col.button("Mở", key=f"open_{pid}", type="primary", use_container_width=True):
            _open_project(project)
        with edit_col.popover("Sửa", use_container_width=True):
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
        with delete_col:
            confirmed = confirm_button(
                "Xóa",
                key=f"delete_{pid}",
                icon=":material/delete:",
                title="Xóa dự án?",
                message=(
                    f"Dự án “{project['name']}” và toàn bộ dataset bên trong sẽ bị xóa. "
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


page_shell("Dự án", "Mỗi dự án chứa các dataset và lịch sử làm sạch của chúng.")

token = get_token()
user = get_current_user() or {}

if st.button("Tạo dự án", icon=":material/add:", type="primary"):
    _create_dialog()

projects, error = safe_call("Đang tải dự án…", list_projects, token)
if error is not None:
    error_state(error, key="dashboard")
    st.stop()

projects = sorted(projects, key=lambda p: p["created_at"], reverse=True)

if not projects:
    if empty_state(
        "folder_open",
        "Chưa có dự án nào",
        "Dự án gom các dataset cùng mục đích. Hãy tạo dự án đầu tiên để bắt đầu.",
        cta_label="Tạo dự án đầu tiên",
    ):
        _create_dialog()
    st.stop()

_KPI_COLUMNS = 3


def _kpi_tiles(projects: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Các thẻ KPI (nhãn, giá trị) tính từ ProjectOut của GET /projects.

    Số dataset và điểm chất lượng chỉ hiện khi backend trả dữ liệu tương ứng.
    """
    tiles = [("Số dự án", format_number(len(projects)))]
    if all(p.get("dataset_count") is not None for p in projects):
        tiles.append(("Số dataset", format_number(sum(p["dataset_count"] for p in projects))))
    scores = [
        p["average_quality_score"] for p in projects if p.get("average_quality_score") is not None
    ]
    if scores:
        tiles.append(
            (
                "Điểm TB theo dự án",
                f"{sum(scores) / len(scores):.1f}".replace(".", ",") + " / 100",
            )
        )
    return tiles


tiles = _kpi_tiles(projects)
for start in range(0, len(tiles), _KPI_COLUMNS):
    for column, (label, value) in zip(
        st.columns(_KPI_COLUMNS), tiles[start : start + _KPI_COLUMNS], strict=False
    ):
        with column:
            help_text = (
                "Trung bình các điểm trung bình theo dự án mà backend trả về."
                if label == "Điểm TB theo dự án"
                else None
            )
            metric_card(label, value, help=help_text)

filter_col, scope_col, count_col = st.columns([3, 2, 1], vertical_alignment="bottom")
search = filter_col.text_input("Tìm theo tên dự án", key="project_search")
scope = scope_col.radio(
    "Hiển thị",
    ["Tất cả", "Gần đây"],
    horizontal=True,
    key="project_scope",
)
filtered_projects = [
    project for project in projects if search.casefold() in project["name"].casefold()
]
if scope == "Gần đây":
    filtered_projects = filtered_projects[:_RECENT_PROJECT_COUNT]
count_col.caption(f"{format_number(len(filtered_projects))} dự án")

st.subheader("Danh sách dự án")
if not filtered_projects:
    empty_state(
        "search_off",
        "Không tìm thấy dự án",
        "Thử từ khóa khác hoặc chọn bộ lọc Tất cả.",
    )
else:
    selected_project_id = get_context().get("project_id")
    for start in range(0, len(filtered_projects), _COLUMNS):
        for column, project in zip(
            st.columns(_COLUMNS), filtered_projects[start : start + _COLUMNS], strict=False
        ):
            with column:
                _project_card(
                    project,
                    user.get("id"),
                    selected=project["id"] == selected_project_id,
                )

selected_project = next(
    (project for project in projects if project["id"] == get_context().get("project_id")),
    None,
)
if selected_project is not None:
    with section(f'Dataset trong “{selected_project["name"]}”'):
        if st.button("Tải dataset lên", icon=":material/upload:", key="project_upload"):
            _open_project(selected_project, to_upload=True)

        summaries, error = project_dataset_summaries(token, selected_project["id"])
        if error is not None:
            error_state(error, key="project_datasets")
        elif not summaries:
            st.caption("Dự án này chưa có dataset.")
        else:
            for summary in summaries:
                dataset = summary["dataset"]
                version = summary["version"]
                quality = summary["quality"]
                with st.container(border=True):
                    name_col, open_col = st.columns([5, 1], vertical_alignment="center")
                    name_col.markdown(f"**{dataset['original_filename']}**")
                    name_col.caption(
                        f"Phiên bản v{version['version_number']} · "
                        f"{format_number(version['row_count'])} dòng · "
                        f"{format_number(version['column_count'])} cột"
                    )
                    score = f"{quality['overall_score']:.1f}".replace(".", ",")
                    name_col.caption(f"Điểm chất lượng: {score} / 100")
                    if open_col.button(
                        "Mở",
                        key=f"open_dataset_{dataset['id']}",
                        use_container_width=True,
                    ):
                        _open_dataset(selected_project, summary)
