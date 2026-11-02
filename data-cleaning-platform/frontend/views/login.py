"""Trang đăng nhập và đăng ký tài khoản."""

import base64
import re
from typing import Any

import streamlit as st

from api_client import APIConnectionError, APIError, get_me, login, register
from components.navigation import PRODUCT_NAME, PRODUCT_SHORT_NAME, PRODUCT_TAGLINE
from components.theme import ASSETS_DIR
from components.ui import data_source_banner, error_state, page_shell, safe_call
from state import set_flash, set_logged_in

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 8  # khớp RegisterRequest.password(min_length=8) của backend

# Đăng nhập thất bại luôn hiện một câu chung, không chuyển tiếp thông báo của backend: tránh lộ
# email có tồn tại hay tài khoản đang bị khóa hay không (chống dò tài khoản).
_LOGIN_FAILED_MESSAGE = "Email hoặc mật khẩu không đúng."
_LOGIN_FAILURE_STATUSES = frozenset({400, 401, 403, 404})


def _brand_html() -> str:
    mark = base64.b64encode((ASSETS_DIR / "logo-mark.svg").read_bytes()).decode()
    return (
        '<div class="dc-brand">'
        f'<img class="dc-brand__mark" alt="" src="data:image/svg+xml;base64,{mark}">'
        f'<div class="dc-brand__name" role="heading" aria-level="1">{PRODUCT_NAME}</div>'
        f'<p class="dc-brand__tagline">{PRODUCT_TAGLINE}</p>'
        "</div>"
    )


def _authenticate(call: Any, *args: str) -> tuple[str, dict[str, Any]]:
    """Gọi login/register rồi lấy thông tin user; trả (token, user)."""
    token = call(*args)["access_token"]
    return token, get_me(token)


def _show_error(exc: APIError, key: str) -> None:
    """Lỗi nghiệp vụ (sai mật khẩu, email trùng...) hiện gọn; lỗi kết nối/máy chủ hiện đầy đủ."""
    if isinstance(exc, APIConnectionError) or exc.status_code >= 500:
        error_state(exc, key=key)
    else:
        st.error(exc.detail, icon=":material/error:")


def _show_problems(problems: list[str]) -> None:
    st.error("\n".join(f"- {p}" for p in problems), icon=":material/error:")


def _sign_in(
    call: Any,
    args: tuple[str, ...],
    message: str,
    key: str,
    *,
    failed_message: str | None = None,
) -> None:
    """Đăng nhập/đăng ký; thành công thì lưu phiên, đặt thông báo và nạp lại để vào Trang chủ.

    Args:
        failed_message: nếu có, thay cho thông báo của backend khi bị từ chối (4xx xác thực).
    """
    result, error = safe_call("Đang xử lý…", _authenticate, call, *args)
    if error is not None:
        if (
            failed_message
            and not isinstance(error, APIConnectionError)
            and error.status_code in _LOGIN_FAILURE_STATUSES
        ):
            st.error(failed_message, icon=":material/error:")
        else:
            _show_error(error, key)
        return
    token, user = result
    set_logged_in(token, user)
    set_flash(message, "success")
    st.rerun()


def _login_tab() -> None:
    with st.form("login_form", border=False):
        email = st.text_input("Email", placeholder="ten@congty.vn", autocomplete="email")
        password = st.text_input("Mật khẩu", type="password", autocomplete="current-password")
        submitted = st.form_submit_button(
            "Đăng nhập", type="primary", use_container_width=True, icon=":material/login:"
        )
    if not submitted:
        return

    email = email.strip()
    problems = []
    if not email:
        problems.append("Vui lòng nhập email.")
    elif not _EMAIL_RE.match(email):
        problems.append("Email không hợp lệ.")
    if not password:
        problems.append("Vui lòng nhập mật khẩu.")
    if problems:
        _show_problems(problems)
        return
    _sign_in(
        login,
        (email, password),
        "Đăng nhập thành công. Chào mừng bạn quay lại!",
        "login_err",
        failed_message=_LOGIN_FAILED_MESSAGE,
    )


def _register_tab() -> None:
    with st.form("register_form", border=False):
        full_name = st.text_input("Họ và tên", autocomplete="name")
        email = st.text_input(
            "Email", placeholder="ten@congty.vn", key="reg_email", autocomplete="email"
        )
        password = st.text_input(
            "Mật khẩu",
            type="password",
            key="reg_password",
            help=f"Tối thiểu {_MIN_PASSWORD_LENGTH} ký tự.",
            autocomplete="new-password",
        )
        confirm = st.text_input(
            "Nhập lại mật khẩu", type="password", key="reg_confirm", autocomplete="new-password"
        )
        submitted = st.form_submit_button(
            "Tạo tài khoản", type="primary", use_container_width=True, icon=":material/person_add:"
        )
    if not submitted:
        return

    full_name, email = full_name.strip(), email.strip()
    problems = []
    if not full_name:
        problems.append("Vui lòng nhập họ và tên.")
    if not email:
        problems.append("Vui lòng nhập email.")
    elif not _EMAIL_RE.match(email):
        problems.append("Email không hợp lệ.")
    if len(password) < _MIN_PASSWORD_LENGTH:
        problems.append(f"Mật khẩu cần có ít nhất {_MIN_PASSWORD_LENGTH} ký tự.")
    elif password != confirm:
        problems.append("Mật khẩu nhập lại không khớp.")
    if problems:
        _show_problems(problems)
        return
    _sign_in(
        register,
        (email, password, full_name),
        f"Tạo tài khoản thành công. Chào mừng bạn đến với {PRODUCT_SHORT_NAME}!",
        "register_err",
    )


page_shell(public=True)

_, center, _ = st.columns([1, 1.5, 1])
with center:
    st.markdown(_brand_html(), unsafe_allow_html=True)
    data_source_banner(show_hint=True)
    with st.container(border=True):
        tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])
        with tab_login:
            _login_tab()
        with tab_register:
            _register_tab()
