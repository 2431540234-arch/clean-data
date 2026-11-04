"""Trang Quản trị người dùng: chỉ admin. Xem danh sách, khóa/mở, đổi quyền, đặt lại mật khẩu."""

from typing import Any

import streamlit as st

from api_client import (
    APIConnectionError,
    admin_list_users,
    admin_reset_password,
    admin_update_user,
)
from components.formatting import format_date, format_number
from components.labels import ROLE_LABELS, role_label
from components.ui import (
    admin_subnav,
    badge_html,
    confirm_button,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
)
from components.user_table import render_user_table, user_matches
from state import get_context, get_current_user, get_token, set_context, set_flash

_ROLE_FILTERS = {"Tất cả quyền": None, **{label: role for role, label in ROLE_LABELS.items()}}
_STATUS_FILTERS = {"Mọi trạng thái": None, "Đang hoạt động": True, "Đã khóa": False}


def _act(label: str, func: Any, *args: Any, message: str, **kwargs: Any) -> Any:
    """Gọi API quản trị; thành công thì báo toast và nạp lại, lỗi hiện tại chỗ."""
    result, error = safe_call(label, func, get_token(), *args, **kwargs)
    if error is not None:
        if isinstance(error, APIConnectionError) or error.status_code >= 500:
            error_state(error, key="admin_users_action")
        else:
            st.error(error.detail, icon=":material/error:")
        return None
    set_flash(message)
    return result


def _manage_panel(user: dict[str, Any], me: int | None) -> None:
    uid = user["id"]
    is_me = uid == me
    status = (
        badge_html("Đang hoạt động", "success")
        if user["is_active"]
        else badge_html("Đã khóa", "error")
    )
    with section(f"Quản lý: {user['full_name']}"):
        st.markdown(
            f"{user['email']} · {badge_html(role_label(user['role']), 'primary')} {status}"
            f" · tham gia {format_date(user['created_at'])}",
            unsafe_allow_html=True,
        )
        revealed = get_context().get("reset_result")
        if revealed and revealed["user_id"] == uid:
            st.success(
                "Đã đặt lại mật khẩu. Mật khẩu tạm chỉ hiển thị một lần, hãy gửi cho người dùng "
                "và yêu cầu đổi ngay:",
                icon=":material/key:",
            )
            st.code(revealed["password"], language=None)
            if st.button("Ẩn mật khẩu", key=f"hide_reset_{uid}", icon=":material/visibility_off:"):
                set_context(reset_result=None)
                st.rerun()
        if is_me:
            st.info(
                "Đây là tài khoản của bạn: không thể tự khóa hay hạ quyền. "
                "Đổi mật khẩu ở trang Tài khoản.",
                icon=":material/info:",
            )
            return

        role_col, lock_col, reset_col = st.columns(3)
        with role_col:
            roles = list(ROLE_LABELS)
            new_role = st.selectbox(
                "Quyền",
                roles,
                index=roles.index(user["role"]),
                format_func=role_label,
                key=f"role_{uid}",
            )
            if confirm_button(
                "Lưu quyền",
                key=f"save_role_{uid}",
                icon=":material/manage_accounts:",
                disabled=new_role == user["role"],
                title="Đổi quyền người dùng?",
                message=(
                    f"“{user['full_name']}” sẽ trở thành {role_label(new_role).lower()}. "
                    "Quyền mới có hiệu lực ở lần tải trang kế tiếp của họ."
                ),
                confirm_label="Đổi quyền",
                warning=new_role == "admin",
            ) and _act(
                "Đang lưu quyền…",
                admin_update_user,
                uid,
                role=new_role,
                message=f"Đã đổi quyền của {user['full_name']} thành {role_label(new_role)}.",
            ):
                st.rerun()
        with lock_col:
            st.caption("Trạng thái tài khoản")
            lock = user["is_active"]
            if confirm_button(
                "Khóa tài khoản" if lock else "Mở khóa tài khoản",
                key=f"toggle_active_{uid}",
                icon=":material/lock:" if lock else ":material/lock_open:",
                title="Khóa tài khoản?" if lock else "Mở khóa tài khoản?",
                message=(
                    f"“{user['full_name']}” sẽ không đăng nhập được cho tới khi được mở khóa."
                    if lock
                    else f"“{user['full_name']}” sẽ đăng nhập lại được."
                ),
                confirm_label="Khóa" if lock else "Mở khóa",
                warning=lock,
            ) and _act(
                "Đang cập nhật…",
                admin_update_user,
                uid,
                is_active=not lock,
                message=("Đã khóa" if lock else "Đã mở khóa") + f" tài khoản {user['full_name']}.",
            ):
                st.rerun()
        with reset_col:
            st.caption("Mật khẩu")
            if confirm_button(
                "Đặt lại mật khẩu",
                key=f"reset_{uid}",
                icon=":material/key:",
                title="Đặt lại mật khẩu?",
                message=(
                    f"Mật khẩu hiện tại của “{user['full_name']}” sẽ mất hiệu lực và được thay "
                    "bằng một mật khẩu tạm."
                ),
                confirm_label="Đặt lại",
                warning=True,
            ):
                result = _act(
                    "Đang đặt lại mật khẩu…",
                    admin_reset_password,
                    uid,
                    message=f"Đã đặt lại mật khẩu của {user['full_name']}.",
                )
                if result is not None:
                    if result.get("new_password"):
                        set_context(
                            reset_result={"user_id": uid, "password": result["new_password"]}
                        )
                    st.rerun()


page_shell("Quản trị người dùng", "Khóa/mở tài khoản, đổi quyền, đặt lại mật khẩu", admin=True)
admin_subnav()

users, error = safe_call("Đang tải danh sách người dùng…", admin_list_users, get_token())
if error is not None:
    error_state(error, key="admin_users")
    st.stop()
if not users:
    empty_state("group", "Chưa có người dùng nào", "Danh sách người dùng đang trống.")
    st.stop()

me = (get_current_user() or {}).get("id")
for cell, (label, value) in zip(
    st.columns(4),
    [
        ("Tổng người dùng", format_number(len(users))),
        ("Đang hoạt động", format_number(sum(1 for u in users if u["is_active"]))),
        ("Đã khóa", format_number(sum(1 for u in users if not u["is_active"]))),
        ("Quản trị viên", format_number(sum(1 for u in users if u["role"] == "admin"))),
    ],
    strict=True,
):
    with cell:
        metric_card(label, value)

search_col, role_col, status_col = st.columns([3, 2, 2])
query = search_col.text_input(
    "Tìm kiếm", placeholder="Tìm theo tên hoặc email", key="admin_user_query"
)
role_choice = role_col.selectbox("Quyền", list(_ROLE_FILTERS), key="admin_user_role_filter")
status_choice = status_col.selectbox(
    "Trạng thái", list(_STATUS_FILTERS), key="admin_user_status_filter"
)

shown = [
    u
    for u in sorted(users, key=lambda u: u["id"])
    if user_matches(u, query, _ROLE_FILTERS[role_choice], _STATUS_FILTERS[status_choice])
]
if not shown:
    st.info("Không có người dùng nào khớp bộ lọc.", icon=":material/filter_alt_off:")
    st.stop()

st.caption(f"{format_number(len(shown))}/{format_number(len(users))} người dùng")
render_user_table(shown, me)

by_id = {u["id"]: u for u in shown}
chosen = st.selectbox(
    "Chọn người dùng để quản lý",
    list(by_id),
    index=None,
    placeholder="Chọn một người dùng",
    format_func=lambda uid: f"{by_id[uid]['full_name']} · {by_id[uid]['email']}",
    key="admin_user_selected",
)
if chosen is not None:
    _manage_panel(by_id[chosen], me)
