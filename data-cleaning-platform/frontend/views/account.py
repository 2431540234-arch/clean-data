"""Trang Tài khoản: xem thông tin cá nhân và đổi mật khẩu."""

from html import escape

import streamlit as st

from api_client import (
    APIConnectionError,
    APIError,
    change_password,
    get_me,
    list_projects,
    list_rule_templates,
)
from components.formatting import format_date, format_number
from components.ui import badge_html, error_state, metric_card, page_shell, safe_call, section
from state import get_current_user, get_token, set_flash, set_logged_in

_MIN_PASSWORD_LENGTH = 8  # khớp ChangePasswordRequest.new_password(min_length=8) của backend


def _profile(user: dict) -> None:
    name = str(user.get("full_name") or user.get("email") or "Người dùng")
    role = (
        badge_html("Quản trị viên", "primary")
        if user.get("role") == "admin"
        else badge_html("Người dùng")
    )
    status = (
        badge_html("Đang hoạt động", "success")
        if user.get("is_active", True)
        else badge_html("Đã khóa", "error")
    )
    tiles = _usage_tiles()
    with section():
        profile_col, *tile_cols = st.columns([2.2, *([1] * len(tiles))])
        with profile_col:
            st.markdown(
                '<div class="dc-user-card dc-user-card--plain">'
                '<div class="dc-user-card__avatar" aria-hidden="true">'
                f"{escape(name[:1].upper())}</div>"
                '<div class="dc-user-card__body">'
                f'<div class="dc-user-card__name">{escape(name)}</div>'
                f'<div class="dc-user-card__email">{escape(str(user.get("email", "")))}</div>'
                f"{role} {status}</div></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Tham gia từ {format_date(user.get('created_at'))}")
        for column, (label, value) in zip(tile_cols, tiles, strict=True):
            with column:
                metric_card(label, value)


def _usage_tiles() -> list[tuple[str, str]]:
    """Số dự án, dataset và quy tắc của người dùng; thẻ nào backend chưa trả đủ thì ẩn."""
    projects, error = safe_call("Đang tải số liệu tài khoản…", list_projects, get_token())
    if error is not None:
        return []
    tiles = [("Dự án", format_number(len(projects)))]
    if all(p.get("dataset_count") is not None for p in projects):
        tiles.append(("Dataset", format_number(sum(p["dataset_count"] for p in projects))))
    try:
        rules = sum(len(list_rule_templates(get_token(), p["id"])) for p in projects)
    except APIError:
        return tiles
    return [*tiles, ("Quy tắc của tôi", format_number(rules))]


def _personal_info(user: dict) -> None:
    """Họ tên và email chỉ để xem: backend chưa có endpoint cập nhật hồ sơ."""
    with section("Thông tin cá nhân"):
        # Hiển thị chữ thường (không dùng ô nhập bị tắt) để giữ độ tương phản đạt WCAG AA.
        for label, value in (("Họ và tên", user.get("full_name")), ("Email", user.get("email"))):
            st.caption(label)
            st.markdown(f"**{escape(str(value or '—'))}**")
        st.caption("Họ tên và email không thể đổi tại đây. Liên hệ quản trị viên nếu cần.")


def _password_form() -> None:
    with section(
        "Đổi mật khẩu", caption=f"Mật khẩu mới cần có ít nhất {_MIN_PASSWORD_LENGTH} ký tự."
    ):
        with st.form("change_password_form", clear_on_submit=True, border=False):
            old = st.text_input(
                "Mật khẩu hiện tại", type="password", autocomplete="current-password"
            )
            new = st.text_input("Mật khẩu mới", type="password", autocomplete="new-password")
            confirm = st.text_input(
                "Nhập lại mật khẩu mới", type="password", autocomplete="new-password"
            )
            st.info(
                "Sau khi đổi, các phiên đăng nhập khác sẽ hết hiệu lực. "
                "Bạn vẫn ở lại trang này.",
                icon=":material/info:",
            )
            submitted = st.form_submit_button("Đổi mật khẩu", type="primary", icon=":material/key:")
        if not submitted:
            return

        problems = []
        if not old:
            problems.append("Vui lòng nhập mật khẩu hiện tại.")
        if len(new) < _MIN_PASSWORD_LENGTH:
            problems.append(f"Mật khẩu mới cần có ít nhất {_MIN_PASSWORD_LENGTH} ký tự.")
        elif new == old:
            problems.append("Mật khẩu mới phải khác mật khẩu hiện tại.")
        elif new != confirm:
            problems.append("Mật khẩu nhập lại không khớp.")
        if problems:
            st.error("\n".join(f"- {p}" for p in problems), icon=":material/error:")
            return

        result, error = safe_call("Đang đổi mật khẩu…", change_password, get_token(), old, new)
        if error is None:
            # Backend vô hiệu mọi token cũ khi đổi mật khẩu và trả token mới: nhận lại để người
            # dùng ở lại trang (không bị đăng xuất giữa chừng).
            new_token = (result or {}).get("access_token")
            if new_token:
                set_logged_in(new_token, get_current_user() or {})
            set_flash("Đã đổi mật khẩu.")
            st.rerun()
        elif isinstance(error, APIConnectionError) or error.status_code >= 500:
            error_state(error, key="change_password")
        else:
            st.error(error.detail, icon=":material/error:")


page_shell("Tài khoản", "Thông tin cá nhân và mật khẩu")

user = get_current_user() or {}
fresh, error = safe_call("Đang tải thông tin tài khoản…", get_me, get_token())
if error is not None:
    if error.status_code == 401:
        error_state(error, key="account")  # phiên hết hạn: nút Đăng nhập lại
        st.stop()
    st.warning("Không cập nhật được thông tin mới nhất; đang hiển thị thông tin đã lưu.")
else:
    user = fresh
    set_logged_in(get_token(), fresh)  # phòng khi quyền/họ tên bị admin đổi

_profile(user)
info_col, password_col = st.columns(2, gap="large")
with info_col:
    _personal_info(user)
with password_col:
    _password_form()
