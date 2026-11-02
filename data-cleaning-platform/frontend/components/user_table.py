"""Bảng danh sách người dùng cho trang quản trị (chỉ xem; thao tác ở khung quản lý của trang)."""

from typing import Any

import pandas as pd

from components.formatting import format_date
from components.labels import role_label
from components.ui import data_table

_MAX_HEIGHT = 420


def user_matches(user: dict[str, Any], query: str, role: str | None, active: bool | None) -> bool:
    """User khớp ô tìm kiếm (tên/email, không phân biệt hoa thường) và bộ lọc quyền/trạng thái."""
    needle = query.strip().lower()
    if needle and needle not in f"{user['full_name']} {user['email']}".lower():
        return False
    if role is not None and user["role"] != role:
        return False
    return active is None or user["is_active"] == active


def render_user_table(users: list[dict[str, Any]], current_user_id: int | None = None) -> None:
    """Bảng người dùng: họ tên (đánh dấu "(bạn)"), email, quyền, trạng thái, ngày tham gia."""
    table = pd.DataFrame(
        {
            "ID": [u["id"] for u in users],
            "Họ tên": [
                f"{u['full_name']} (bạn)" if u["id"] == current_user_id else u["full_name"]
                for u in users
            ],
            "Email": [u["email"] for u in users],
            "Quyền": [role_label(u["role"]) for u in users],
            "Trạng thái": ["Đang hoạt động" if u["is_active"] else "Đã khóa" for u in users],
            "Tham gia": [format_date(u["created_at"]) for u in users],
        }
    )
    data_table(table, height=min(_MAX_HEIGHT, 56 + 36 * len(table)))
