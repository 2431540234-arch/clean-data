"""Ngữ cảnh dataset đang làm việc: thanh thông tin dùng chung cho các bước 2-6 của quy trình.

Ngữ cảnh (project/dataset/version) lưu trong state.get_context(). Version luôn lấy theo
`current_version_id` của dataset từ API (nguồn sự thật), nên undo/restore tự phản ánh.
"""

from dataclasses import dataclass
from typing import Any

import streamlit as st

from api_client import APIError, get_dataset, list_dataset_versions
from components.navigation import get_page
from components.ui import empty_state, error_state, safe_call
from state import get_context, get_token, set_context, set_flash


@dataclass(frozen=True)
class ActiveDataset:
    """Dataset đang làm việc cùng phiên bản hiện tại của nó (DatasetOut, DatasetVersionOut)."""

    dataset: dict[str, Any]
    version: dict[str, Any]


def open_dataset_form(key: str) -> None:
    """Form mở lại một dataset đã tải lên bằng ID.

    TODO(backend): thay bằng danh sách dataset của project khi backend có endpoint liệt kê
    dataset theo project (docs/BACKEND_TODO.md, mục 2 #1). Hiện chỉ có GET /datasets/{id}.
    """
    dataset_id = st.number_input(
        "Dataset ID", min_value=1, step=1, value=None, format="%d", placeholder="Nhập ID", key=key
    )
    if st.button("Mở dataset", key=f"{key}_open", disabled=dataset_id is None):
        dataset, error = safe_call("Đang mở dataset…", get_dataset, get_token(), int(dataset_id))
        if error is not None:
            st.error(error.detail, icon=":material/error:")
            return
        set_context(
            project_id=dataset["project_id"],
            project_name=None,
            dataset_id=dataset["id"],
            dataset_name=dataset["original_filename"],
            version_id=dataset["current_version_id"],
            upload_result=None,
        )
        set_flash(f"Đã mở dataset “{dataset['original_filename']}”.")
        st.rerun()


def _load(token: str, dataset_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset = get_dataset(token, dataset_id)
    versions = list_dataset_versions(token, dataset_id)
    version = next((v for v in versions if v["id"] == dataset["current_version_id"]), None)
    if version is None:
        raise APIError(404, "Không tìm thấy phiên bản hiện tại của dataset.")
    return dataset, version


def _no_dataset(message: str | None = None) -> None:
    if message:
        st.warning(message, icon=":material/warning:")
    empty_state(
        "database",
        "Chưa chọn dataset",
        "Tải dữ liệu lên hoặc mở lại dataset đã có để tiếp tục.",
        cta_label="Tải dữ liệu lên",
        cta_page="upload",
    )
    with st.expander("Mở dataset đã tải lên trước đó"):
        open_dataset_form("ctx_open_empty")


def dataset_context_bar() -> ActiveDataset:
    """Hiện thanh dataset đang làm việc và trả về ActiveDataset.

    Chưa chọn dataset (hoặc dataset không còn truy cập được) thì hiện trạng thái rỗng có lối
    dẫn tới bước Tải lên rồi dừng trang (st.stop()); lỗi API khác hiện error_state rồi dừng.
    """
    context = get_context()
    dataset_id = context.get("dataset_id")
    if not dataset_id:
        _no_dataset()
        st.stop()

    info, error = safe_call("Đang tải dataset…", _load, get_token(), dataset_id)
    if error is not None:
        if error.status_code in (403, 404):
            set_context(dataset_id=None, dataset_name=None, version_id=None, upload_result=None)
            _no_dataset(f"Không mở được dataset #{dataset_id}: {error.detail}")
        else:
            error_state(error, key="dataset_context")
        st.stop()

    dataset, version = info
    set_context(version_id=version["id"], dataset_name=dataset["original_filename"])
    project = context.get("project_name") or f"#{dataset['project_id']}"
    with st.container(border=True):
        left, right = st.columns([5, 2], vertical_alignment="center")
        left.markdown(
            f"**{dataset['original_filename']}** · Phiên bản {version['version_number']}"
            f" · {version['row_count']:,} dòng × {version['column_count']} cột".replace(",", ".")
        )
        left.caption(f"Project: {project}")
        with right.popover("Đổi dataset", icon=":material/folder_open:", use_container_width=True):
            open_dataset_form("ctx_open_bar")
            st.divider()
            if st.button("Tải file mới lên", icon=":material/upload_file:", key="ctx_goto_upload"):
                st.switch_page(get_page("upload").file)
    return ActiveDataset(dataset=dataset, version=version)
