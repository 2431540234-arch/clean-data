"""Trang Nhật ký hoạt động (audit log): hành động của chính mình hoặc toàn hệ thống (admin)."""

from typing import Any

import pandas as pd
import streamlit as st

from api_client import admin_list_users, audit_all, audit_me
from components.formatting import format_datetime, format_number, to_vn_datetime
from components.labels import action_label, entity_label
from components.navigation import get_page
from components.ui import (
    data_table,
    empty_state,
    error_state,
    page_shell,
    safe_call,
)
from state import get_token, is_admin

_MAX_ROWS = 500  # số bản ghi tối đa hiển thị trong bảng (mới nhất trước)


def _user_names() -> dict[int, str]:
    """id -> họ tên (chỉ admin gọi được); lỗi thì trả rỗng, giao diện sẽ hiện "#id"."""
    users, error = safe_call("Đang tải danh sách người dùng…", admin_list_users, get_token())
    if error is not None:
        return {}
    return {u["id"]: u["full_name"] for u in users}


def _within(log: dict[str, Any], date_range: tuple) -> bool:
    """Bản ghi nằm trong khoảng ngày (theo giờ VN) đã chọn; chưa chọn đủ 2 mốc thì không lọc."""
    if len(date_range) != 2:
        return True
    created = to_vn_datetime(log["created_at"])
    return created is not None and date_range[0] <= created.date() <= date_range[1]


def _table(logs: list[dict[str, Any]], names: dict[int, str] | None) -> pd.DataFrame:
    rows = []
    for log in logs[:_MAX_ROWS]:
        row = {
            "Thời gian": format_datetime(log["created_at"]),
            "Hành động": action_label(log["action"]),
            "Đối tượng": entity_label(log["entity_type"], log["entity_id"]),
        }
        if names is not None:
            row["Người thực hiện"] = names.get(log["user_id"], f"#{log['user_id']}")
        row["IP"] = log["ip_address"] or "—"
        rows.append(row)
    return pd.DataFrame(rows)


def _detail(logs: list[dict[str, Any]]) -> None:
    by_id = {log["id"]: log for log in logs}
    chosen = st.selectbox(
        "Xem chi tiết một bản ghi",
        list(by_id)[:_MAX_ROWS],
        index=None,
        placeholder="Chọn một bản ghi để xem trạng thái trước/sau",
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
    before.markdown("**Trước**")
    before.json(log["old_value"] or {})
    after.markdown("**Sau**")
    after.json(log["new_value"] or {})


page_shell("Nhật ký hoạt động", "Các hành động đã thực hiện trên hệ thống")

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

actions = sorted({log["action"] for log in logs})
filter_actions, filter_dates = st.columns([3, 2])
selected_actions = filter_actions.multiselect(
    "Hành động",
    actions,
    format_func=action_label,
    placeholder="Tất cả hành động",
    key="audit_actions",
)
date_range = filter_dates.date_input(
    "Khoảng ngày", value=(), format="DD/MM/YYYY", key="audit_range"
)

shown = [
    log
    for log in logs
    if (not selected_actions or log["action"] in selected_actions) and _within(log, date_range)
]
if not shown:
    st.info("Không có bản ghi nào khớp bộ lọc.", icon=":material/filter_alt_off:")
    st.stop()

st.caption(
    f"{format_number(len(shown))}/{format_number(len(logs))} bản ghi, mới nhất trước"
    + (f" (hiển thị {_MAX_ROWS} bản ghi đầu)" if len(shown) > _MAX_ROWS else "")
)
data_table(
    _table(shown, _user_names() if everyone else None), height=min(460, 56 + 36 * len(shown))
)
_detail(shown)

if st.button("Về Trang chủ", icon=":material/home:"):
    st.switch_page(get_page("home").file)
