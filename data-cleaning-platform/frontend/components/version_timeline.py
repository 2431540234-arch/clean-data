"""Hiển thị lịch sử các phiên bản dataset dạng timeline, kèm nút xem chi tiết và khôi phục."""

from typing import Any

import streamlit as st

from components.formatting import format_datetime, format_number
from components.ui import badge_html, confirm_button


def can_undo(versions: list[dict[str, Any]], current_id: int) -> bool:
    """Hoàn tác được khi phiên bản hiện tại có phiên bản cha (backend: parent_version_id)."""
    current = next((v for v in versions if v["id"] == current_id), None)
    return bool(current and current["parent_version_id"] is not None)


def can_redo(versions: list[dict[str, Any]], current_id: int) -> bool:
    """Làm lại được khi có phiên bản con của phiên bản hiện tại."""
    return any(v["parent_version_id"] == current_id for v in versions)


def delta_text(value: int, unit: str) -> str:
    """Ví dụ "+3 dòng" hoặc "−1 dòng"."""
    sign = "+" if value > 0 else "−"
    return f"{sign}{format_number(abs(value))} {unit}"


def render_version_timeline(
    versions: list[dict[str, Any]],
    current_id: int,
    current_user_id: int | None,
    selected_id: int | None = None,
) -> tuple[int | None, int | None]:
    """Vẽ các phiên bản từ mới đến cũ, đánh dấu phiên bản hiện tại và phiên bản đang xem.

    Returns:
        (id phiên bản vừa xác nhận khôi phục, id phiên bản vừa bấm "Xem"); None nếu không có.
    """
    by_id = {v["id"]: v for v in versions}
    restore_id = view_id = None
    for version in sorted(versions, key=lambda v: v["version_number"], reverse=True):
        parent = by_id.get(version["parent_version_id"])
        badges = []
        if version["id"] == current_id:
            badges.append(badge_html("Hiện tại", "success"))
        if parent is None:
            badges.append(badge_html("Bản gốc", "primary"))
        st.markdown(
            f"**Phiên bản {version['version_number']}** {' '.join(badges)}",
            unsafe_allow_html=True,
        )
        st.write(version.get("change_summary") or "—")
        facts = [
            f"{format_number(version['row_count'])} dòng × {version['column_count']} cột",
            format_datetime(version["created_at"]),
            "bởi bạn"
            if version["created_by"] == current_user_id
            else f"bởi người dùng #{version['created_by']}",
        ]
        if parent is not None:
            facts.insert(1, f"từ phiên bản {parent['version_number']}")
            changes = []
            if version["row_count"] != parent["row_count"]:
                changes.append(delta_text(version["row_count"] - parent["row_count"], "dòng"))
            if version["column_count"] != parent["column_count"]:
                changes.append(delta_text(version["column_count"] - parent["column_count"], "cột"))
            if changes:
                facts.insert(1, " · ".join(changes))
        st.caption(" · ".join(facts))

        view_col, restore_col, _ = st.columns([1.3, 1.9, 2])
        with view_col:
            if st.button(
                "Đang xem" if version["id"] == selected_id else "Xem",
                key=f"view_{version['id']}",
                disabled=version["id"] == selected_id,
                use_container_width=True,
            ):
                view_id = version["id"]
        if version["id"] != current_id:
            with restore_col:
                if confirm_button(
                    "Khôi phục",
                    key=f"restore_{version['id']}",
                    icon=":material/restore:",
                    title=f"Khôi phục phiên bản {version['version_number']}?",
                    message=(
                        f"Phiên bản {version['version_number']} sẽ trở thành phiên bản hiện "
                        "tại để làm sạch, xem tổng quan và xuất dữ liệu. Các phiên bản khác "
                        "vẫn được giữ nguyên."
                    ),
                    confirm_label="Khôi phục",
                ):
                    restore_id = version["id"]
        st.divider()
    return restore_id, view_id
