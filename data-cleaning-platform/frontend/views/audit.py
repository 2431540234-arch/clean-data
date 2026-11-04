"""Trang Nhật ký hoạt động (audit log): hành động của chính mình hoặc toàn hệ thống (admin)."""

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from api_client import admin_list_users, audit_all, audit_me
from components.formatting import format_datetime, format_number, to_json_text, to_vn_datetime
from components.labels import action_label, entity_label
from components.navigation import get_page
from components.ui import (
    data_table,
    empty_state,
    error_state,
    page_shell,
    safe_call,
    section,
)
from state import get_token, is_admin

_PAGE_SIZE = 20  # số bản ghi mỗi trang của bảng
_ALL = ""  # mục "Tất cả hành động" (dùng selectbox vì placeholder của multiselect không đạt AA)
_FILTER_KEYS = ("audit_from", "audit_to", "audit_actions", "audit_user")


def _users() -> dict[int, dict[str, Any]]:
    """id -> người dùng (chỉ admin gọi được); lỗi thì trả rỗng, giao diện sẽ hiện "#id"."""
    users, error = safe_call("Đang tải danh sách người dùng…", admin_list_users, get_token())
    if error is not None:
        return {}
    return {u["id"]: u for u in users}


def _within(log: dict[str, Any], start: date | None, end: date | None) -> bool:
    """Bản ghi nằm trong khoảng ngày (theo giờ VN); mốc nào chưa chọn thì không giới hạn."""
    if start is None and end is None:
        return True
    created = to_vn_datetime(log["created_at"])
    if created is None:
        return False
    return (start is None or created.date() >= start) and (end is None or created.date() <= end)


def _user_label(user_id: int | None, users: dict[int, dict[str, Any]]) -> str:
    user = users.get(user_id)
    return (user.get("full_name") or user.get("email")) if user else f"#{user_id}"


def _table(logs: list[dict[str, Any]], users: dict[int, dict[str, Any]] | None) -> pd.DataFrame:
    rows = []
    for log in logs:
        row = {"Thời gian": format_datetime(log["created_at"])}
        if users is not None:
            row["Người thực hiện"] = _user_label(log["user_id"], users)
        row["Hành động"] = action_label(log["action"])
        row["Đối tượng"] = entity_label(log["entity_type"], log["entity_id"])
        row["IP"] = log["ip_address"] or "—"
        rows.append(row)
    return pd.DataFrame(rows)


def _detail(logs: list[dict[str, Any]]) -> None:
    by_id = {log["id"]: log for log in logs}
    chosen = st.selectbox(
        "Xem chi tiết một bản ghi",
        list(by_id),
        index=None,
        placeholder="Chọn một bản ghi để xem giá trị cũ và mới",
        format_func=lambda i: f"{format_datetime(by_id[i]['created_at'])} · "
        f"{action_label(by_id[i]['action'])}",
        key="audit_detail",
    )
    if chosen is None:
        return
    log = by_id[chosen]
    if not log["old_value"] and not log["new_value"]:
        st.info("Bản ghi này không có dữ liệu chi tiết.", icon=":material/info:")
        return
    before, after = st.columns(2)
    before.markdown("**Giá trị cũ**")
    before.code(to_json_text(log["old_value"] or {}), language=None)
    after.markdown("**Giá trị mới**")
    after.code(to_json_text(log["new_value"] or {}), language=None)


def _clear_filters() -> None:
    for key in _FILTER_KEYS:
        st.session_state.pop(key, None)
    st.session_state["audit_page"] = 0


def _go_page(delta: int) -> None:
    st.session_state["audit_page"] = st.session_state.get("audit_page", 0) + delta


page_shell(
    "Nhật ký hoạt động", "Mọi thao tác thay đổi dữ liệu, tài khoản và quyền đều được ghi lại"
)

everyone = False
if is_admin():
    everyone = st.toggle(
        "Xem toàn hệ thống",
        key="audit_everyone",
        help="Bật để xem hành động của mọi người dùng; tắt để chỉ xem của bạn.",
    )

logs, error = safe_call("Đang tải nhật ký…", audit_all if everyone else audit_me, get_token())
if error is not None:
    error_state(error, key="audit")
    st.stop()

if not logs:
    empty_state(
        "receipt_long",
        "Chưa có hoạt động nào",
        "Các thao tác như tải lên dữ liệu, áp dụng làm sạch hay hoàn tác sẽ được ghi lại ở đây.",
        cta_label="Tải dữ liệu lên",
        cta_page="upload",
    )
    st.stop()

users = _users() if everyone else None
actions = sorted({log["action"] for log in logs})
with section():
    cols = st.columns([1.1, 1.1, 1.5, 1.5, 0.8] if everyone else [1.1, 1.1, 2, 0.8])
    start = cols[0].date_input("Từ ngày", value=None, format="DD/MM/YYYY", key="audit_from")
    end = cols[1].date_input("Đến ngày", value=None, format="DD/MM/YYYY", key="audit_to")
    selected_action = cols[2].selectbox(
        "Hành động",
        [_ALL, *actions],
        format_func=lambda a: "Tất cả hành động" if a == _ALL else action_label(a),
        key="audit_actions",
    )
    person = ""
    if everyone:
        person = cols[3].text_input("Người dùng", placeholder="Tên hoặc email", key="audit_user")
    with cols[-1]:
        st.markdown('<div style="height: 1.7rem"></div>', unsafe_allow_html=True)
        st.button("Xóa bộ lọc", on_click=_clear_filters, use_container_width=True)

    needle = person.strip().casefold()

    def _matches(log: dict[str, Any]) -> bool:
        if selected_action != _ALL and log["action"] != selected_action:
            return False
        if not _within(log, start, end):
            return False
        if needle:
            user = (users or {}).get(log["user_id"], {})
            haystack = f"{user.get('full_name', '')} {user.get('email', '')}".casefold()
            return needle in haystack
        return True

    shown = [log for log in logs if _matches(log)]
    if not shown:
        st.info("Không có bản ghi nào khớp bộ lọc.", icon=":material/filter_alt_off:")
        st.stop()

    last_page = (len(shown) - 1) // _PAGE_SIZE
    page_index = min(max(st.session_state.get("audit_page", 0), 0), last_page)
    st.session_state["audit_page"] = page_index
    first = page_index * _PAGE_SIZE
    visible = shown[first : first + _PAGE_SIZE]

    data_table(_table(visible, users), height=min(460, 56 + 36 * len(visible)))
    _detail(visible)

    info_col, prev_col, next_col = st.columns([4, 1, 1], vertical_alignment="center")
    info_col.caption(
        f"Hiển thị {first + 1}–{first + len(visible)} trên {format_number(len(shown))} bản ghi"
        + (f" (đã lọc từ {format_number(len(logs))})" if len(shown) != len(logs) else "")
        + ", mới nhất trước"
    )
    prev_col.button(
        "Trước",
        key="audit_prev",
        on_click=_go_page,
        args=(-1,),
        disabled=page_index == 0,
        use_container_width=True,
    )
    next_col.button(
        "Sau",
        key="audit_next",
        on_click=_go_page,
        args=(1,),
        disabled=page_index >= last_page,
        use_container_width=True,
    )

if st.button("Về Trang chủ", icon=":material/home:"):
    st.switch_page(get_page("home").file)
