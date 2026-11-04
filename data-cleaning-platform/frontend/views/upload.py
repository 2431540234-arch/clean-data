"""Trang Tải lên: chọn project, tải file CSV/Excel, chọn sheet (Excel) và xem trước dữ liệu."""

from typing import Any

import pandas as pd
import streamlit as st

from api_client import list_projects, select_sheet, upload_dataset
from components.dataset_context import open_dataset_form
from components.formatting import format_bytes, format_number
from components.navigation import get_page
from components.ui import (
    data_table,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
)
from components.work_context import project_context, uploaded_dataset_context
from state import get_context, get_token, set_context, set_flash

MAX_UPLOAD_MB = 50  # khớp backend MAX_UPLOAD_MB và server.maxUploadSize trong config.toml
_ACCEPTED_TYPES = ["csv", "xlsx"]  # khớp chữ trong khối CSS "Việt hóa ô tải file"
_NONCE_KEY = "upload_nonce"  # đổi key của file_uploader để xóa file đã chọn


def _store_result(result: dict[str, Any], project: dict[str, Any] | None) -> None:
    """Lưu kết quả tải lên và đặt dataset vừa tải làm ngữ cảnh làm việc."""
    set_context(**uploaded_dataset_context(result, project))


def _do_upload(project: dict[str, Any], uploaded: Any) -> None:
    if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
        st.error(f"File vượt quá {MAX_UPLOAD_MB} MB.", icon=":material/error:")
        return
    result, error = safe_call(
        "Đang tải lên và phân tích file…",
        upload_dataset,
        get_token(),
        project["id"],
        uploaded.name,
        uploaded.getvalue(),
        uploaded.type,
    )
    if error is not None:
        if error.status_code >= 500 or error.status_code == 0:
            error_state(error, key="upload_err")
        else:
            st.error(error.detail, icon=":material/error:")
        return
    _store_result(result, project)
    st.rerun()


def _change_upload_project(project_names: dict[int, str]) -> None:
    project_id = st.session_state["upload_project"]
    if project_id == get_context().get("project_id"):
        return
    set_context(**project_context({"id": project_id, "name": project_names[project_id]}))


def _preview_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([row["values"] for row in rows]).fillna("")  # ô trống, không hiện "None"


def _show_result(result: dict[str, Any]) -> None:
    dataset, version = result["dataset"], result["first_version"]
    st.success(f"Đã tải lên “{dataset['original_filename']}”.", icon=":material/check_circle:")

    facts = [
        ("Số dòng", format_number(version["row_count"])),
        ("Số cột", format_number(version["column_count"])),
        ("Dung lượng", format_bytes(dataset["file_size"])),
    ]
    if dataset.get("sheet_name"):
        facts.append(("Sheet", dataset["sheet_name"]))
    else:
        facts.append(("Bảng mã", dataset.get("encoding") or "—"))
    with section("Thông tin file"):
        st.markdown(f"**Tên file:** {dataset['original_filename']}")
        with st.container(key="dc-file-facts"):
            for column, (label, value) in zip(st.columns(len(facts)), facts, strict=True):
                with column:
                    metric_card(label, value)

    sheet_names = result.get("sheet_names") or []
    if len(sheet_names) > 1:
        with section(
            "Chọn sheet",
            caption="File Excel có nhiều sheet. Chọn sheet cần làm sạch.",
        ):
            current = dataset.get("sheet_name")
            index = sheet_names.index(current) if current in sheet_names else 0
            sheet = st.radio(
                "Sheet",
                sheet_names,
                index=index,
                horizontal=True,
                key=f"sheet_{dataset['id']}",
            )
            if sheet != current and st.button("Dùng sheet này", key="use_sheet"):
                new_result, error = safe_call(
                    "Đang đọc sheet…", select_sheet, get_token(), dataset["id"], sheet
                )
                if error is not None:
                    st.error(error.detail, icon=":material/error:")
                else:
                    _store_result(new_result, None)
                    set_flash(f"Đã chuyển sang sheet “{sheet}”.")
                    st.rerun()

    rows = result.get("preview_rows") or []
    with section("Xem trước dữ liệu"):
        if rows:
            st.caption(
                f"{len(rows)} dòng đầu tiên của {format_number(version['row_count'])} dòng."
            )
            data_table(_preview_frame(rows), height=320)
        else:
            st.info("Không có dòng nào để xem trước.", icon=":material/info:")

    if st.button(
        "Tiếp tục: Tổng quan dữ liệu",
        type="primary",
        icon=":material/arrow_forward:",
        use_container_width=True,
    ):
        st.switch_page(get_page("overview").file)


page_shell("Tải lên", "Tải file CSV hoặc Excel lên để bắt đầu làm sạch")

projects, error = safe_call("Đang tải danh sách dự án…", list_projects, get_token())
if error is not None:
    error_state(error, key="upload_projects")
    st.stop()

if not projects:
    empty_state(
        "folder_open",
        "Bạn chưa có dự án nào",
        "Dataset được lưu trong dự án. Hãy tạo dự án trước khi tải dữ liệu.",
        cta_label="Đến Dự án để tạo dự án",
        cta_page="dashboard",
    )
    st.stop()

context = get_context()
result = context.get("upload_result")
projects = sorted(projects, key=lambda p: p["created_at"], reverse=True)
project_ids = [project["id"] for project in projects]
project_names = {project["id"]: project["name"] for project in projects}
if context.get("project_id") in project_ids:
    selected_project_id = context["project_id"]
    if st.session_state.get("upload_project") != selected_project_id:
        st.session_state["upload_project"] = selected_project_id

upload_col, result_col = st.columns([1, 1.35], gap="large")
with upload_col:
    with section(
        "Tải file lên",
        caption=f"Hỗ trợ file CSV và Excel (.xlsx), tối đa {MAX_UPLOAD_MB} MB.",
    ):
        project_id = st.selectbox(
            "Dự án",
            project_ids,
            format_func=project_names.get,
            key="upload_project",
            on_change=_change_upload_project,
            args=(project_names,),
            disabled=result is not None,
        )
        if result is None:
            uploaded = st.file_uploader(
                "Chọn file",
                type=_ACCEPTED_TYPES,
                key=f"upload_file_{st.session_state.get(_NONCE_KEY, 0)}",
            )
            if uploaded is not None:
                st.caption(f"{uploaded.name} · {format_bytes(uploaded.size)}")
            if st.button(
                "Tải lên",
                type="primary",
                icon=":material/upload:",
                disabled=uploaded is None,
                use_container_width=True,
            ):
                selected_project = next(p for p in projects if p["id"] == project_id)
                _do_upload(selected_project, uploaded)
        else:
            st.success(result["dataset"]["original_filename"])
            if st.button("Tải file khác", icon=":material/upload_file:", use_container_width=True):
                st.session_state[_NONCE_KEY] = st.session_state.get(_NONCE_KEY, 0) + 1
                set_context(upload_result=None)
                st.rerun()

    with st.expander("Mở dataset đã tải lên trước đó"):
        open_dataset_form("upload_open")

with result_col:
    if result is not None:
        _show_result(result)
    else:
        with section("Thông tin file"):
            uploaded = st.session_state.get(
                f"upload_file_{st.session_state.get(_NONCE_KEY, 0)}"
            )
            if uploaded is None:
                st.caption("Chọn file để xem thông tin và tải dữ liệu lên.")
            else:
                st.markdown(f"**{uploaded.name}**")
                st.caption(f"Dung lượng: {format_bytes(uploaded.size)}")
                st.caption(f"Loại file: {uploaded.type or 'Không xác định'}")
                st.info("Sau khi tải lên, dữ liệu xem trước sẽ hiển thị tại đây.")
