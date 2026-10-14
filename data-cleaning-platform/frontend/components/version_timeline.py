"""Hiển thị lịch sử các phiên bản dataset dạng timeline, kèm nút undo/redo/khôi phục."""

from typing import Any


def render_version_timeline(versions: list[dict[str, Any]], token: str) -> None:
    """Hiển thị danh sách version theo thời gian, đánh dấu version hiện tại.

    Gợi ý cách làm: dùng st.timeline (hoặc danh sách st.container theo thứ tự),
    mỗi version có nút "Khôi phục" gọi POST /api/v1/versions/{dataset_id}/restore/{version_id}.
    """
    raise NotImplementedError("TODO: render timeline các version kèm hành động khôi phục.")
