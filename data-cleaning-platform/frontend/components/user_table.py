"""Bảng quản lý user dành cho admin: xem danh sách, khóa/mở, đổi quyền."""

from typing import Any


def render_user_table(users: list[dict[str, Any]], token: str) -> None:
    """Hiển thị bảng user kèm nút khóa/mở và đổi quyền cho từng dòng.

    Gợi ý cách làm: dùng st.dataframe để hiển thị danh sách, kết hợp st.selectbox/
    st.button theo từng dòng (hoặc st.data_editor) để gọi api_client tới
    PATCH /api/v1/admin/users/{id}.
    """
    raise NotImplementedError("TODO: render bảng user có hành động khóa/mở, đổi quyền.")
