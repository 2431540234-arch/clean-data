"""Quy tắc đặt ngữ cảnh làm việc (dự án, dataset hiện hành), viết thành hàm thuần.

Không gọi Streamlit nên kiểm thử trực tiếp được; các trang chỉ việc `set_context(**...)` với kết
quả của các hàm này. Nhờ vậy header, trang Dự án và trang Tải lên luôn cùng một quy tắc: chọn hoặc
tạo dự án mới thì dự án đó thành dự án hiện hành và mọi thứ gắn với dự án cũ bị bỏ.
"""

from typing import Any

# Khóa gắn với một dự án/dataset cụ thể: đổi dự án thì xóa sạch để không dùng nhầm dữ liệu cũ.
_PROJECT_SCOPED_RESET: dict[str, Any] = {
    "dataset_id": None,
    "dataset_name": None,
    "version_id": None,
    "upload_result": None,
    "rule_queue": [],
    "rule_queue_version_id": None,
    "preview": None,
    "pending_steps": None,
    "pending_version_id": None,
    "last_applied": None,
    "mapping": None,
}


def project_context(project: dict[str, Any]) -> dict[str, Any]:
    """Giá trị ngữ cảnh khi chọn hoặc vừa tạo một dự án: dự án mới, chưa có dataset nào."""
    return {
        "project_id": project["id"],
        "project_name": project["name"],
        # sao chép danh sách để các lần gọi không dùng chung một đối tượng list
        **{k: list(v) if isinstance(v, list) else v for k, v in _PROJECT_SCOPED_RESET.items()},
    }


def uploaded_dataset_context(
    result: dict[str, Any], project: dict[str, Any] | None
) -> dict[str, Any]:
    """Giá trị ngữ cảnh ngay sau khi tải file: dataset vừa tải thuộc đúng `project`."""
    dataset = result["dataset"]
    values: dict[str, Any] = {
        "dataset_id": dataset["id"],
        "dataset_name": dataset["original_filename"],
        "version_id": dataset["current_version_id"] or result["first_version"]["id"],
        "upload_result": result,
    }
    if project is not None:
        values.update(project_id=project["id"], project_name=project["name"])
    return values
