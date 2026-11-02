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
    stepper,
)
from state import get_context, get_token, set_context, set_flash

MAX_UPLOAD_MB = 50  # khớp backend MAX_UPLOAD_MB và server.maxUploadSize trong config.toml
_ACCEPTED_TYPES = ["csv", "xlsx", "xls"]
_NONCE_KEY = "upload_nonce"  # đổi key của file_uploader để xóa file đã chọn


def _store_result(result: dict[str, Any], project: dict[str, Any] | None) -> None:
    """Lưu kết quả tải lên và đặt dataset vừa tải làm ngữ cảnh làm việc."""
    dataset = result["dataset"]
    values: dict[str, Any] = {
        "dataset_id": dataset["id"],
        "dataset_name": dataset["original_filename"],
        "version_id": dataset["current_version_id"] or result["first_version"]["id"],
        "upload_result": result,
    }
    if project is not None:
        values.update(project_id=project["id"], project_name=project["name"])
    set_context(**values)


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
    set_flash(f"Đã tải lên “{uploaded.name}”.")
    st.rerun()


def _preview_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([row["values"] for row in rows])


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
        facts.append(("Encoding", dataset.get("encoding") or "—"))
    for column, (label, value) in zip(st.columns(len(facts)), facts, strict=True):
        with column:
            metric_card(label, value)

    sheet_names = result.get("sheet_names") or []
    if len(sheet_names) > 1:
        with section("Chọn sheet", caption="File Excel có nhiều sheet. Chọn sheet cần làm sạch."):
            current = dataset.get("sheet_name")
            index = sheet_names.index(current) if current in sheet_names else 0
            sheet = st.selectbox("Sheet", sheet_names, index=index, key=f"sheet_{dataset['id']}")
            if sheet != current and st.button(
                "Dùng sheet này", key="use_sheet", icon=":material/table_view:"
            ):
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
    st.subheader("Xem trước dữ liệu")
    if rows:
        st.caption(f"{len(rows)} dòng đầu tiên của {format_number(version['row_count'])} dòng.")
        data_table(_preview_frame(rows), height=320)
    else:
        st.info("Không có dòng nào để xem trước.", icon=":material/info:")

    next_col, other_col, _ = st.columns([2, 2, 3])
    if next_col.button(
        "Tiếp tục: Tổng quan dữ liệu",
        type="primary",
        icon=":material/arrow_forward:",
        use_container_width=True,
    ):
        st.switch_page(get_page("overview").file)
    if other_col.button("Tải file khác", icon=":material/upload_file:", use_container_width=True):
        st.session_state[_NONCE_KEY] = st.session_state.get(_NONCE_KEY, 0) + 1
        set_context(upload_result=None)
        st.rerun()


page_shell("Tải lên", "Tải file CSV hoặc Excel lên để bắt đầu làm sạch")
stepper("upload")

projects, error = safe_call("Đang tải danh sách project…", list_projects, get_token())
if error is not None:
    error_state(error, key="upload_projects")
    st.stop()

if not projects:
    empty_state(
        "folder_open",
        "Bạn chưa có project nào",
        "Dataset được lưu trong project. Hãy tạo project trước khi tải dữ liệu.",
        cta_label="Đến Dashboard để tạo project",
        cta_page="dashboard",
    )
    st.stop()

context = get_context()
result = context.get("upload_result")
projects = sorted(projects, key=lambda p: p["created_at"], reverse=True)

if result is None:
    with section(
        "Tải file lên",
        caption=(
            f"Hỗ trợ CSV và Excel (.xlsx, .xls), tối đa {MAX_UPLOAD_MB} MB. "
            "Kéo thả file vào khung bên dưới hoặc bấm “Browse files” để chọn."
        ),
    ):
        ids = [p["id"] for p in projects]
        names = {p["id"]: p["name"] for p in projects}
        default = ids.index(context["project_id"]) if context.get("project_id") in ids else 0
        project_id = st.selectbox(
            "Project", ids, index=default, format_func=names.get, key="upload_project"
        )
        uploaded = st.file_uploader(
            "Chọn file",
            type=_ACCEPTED_TYPES,
            key=f"upload_file_{st.session_state.get(_NONCE_KEY, 0)}",
        )
        if st.button(
            "Tải lên",
            type="primary",
            icon=":material/upload:",
            disabled=uploaded is None,
        ):
            _do_upload(next(p for p in projects if p["id"] == project_id), uploaded)
else:
    _show_result(result)

with st.expander("Mở dataset đã tải lên trước đó"):
    open_dataset_form("upload_open")
