"""Quản lý session_state của Streamlit: JWT token, thông tin user, role đang đăng nhập."""

from typing import Any

import streamlit as st

_TOKEN_KEY = "access_token"
_USER_KEY = "current_user"
_FLASH_KEY = "flash_message"
_CONTEXT_KEY = "work_context"


def init_state() -> None:
    """Khởi tạo các key cần thiết trong session_state nếu chưa có."""
    if _TOKEN_KEY not in st.session_state:
        st.session_state[_TOKEN_KEY] = None
    if _USER_KEY not in st.session_state:
        st.session_state[_USER_KEY] = None


def set_logged_in(token: str, user: dict[str, Any]) -> None:
    """Lưu token và thông tin user vào session_state sau khi đăng nhập/đăng ký thành công."""
    st.session_state[_TOKEN_KEY] = token
    st.session_state[_USER_KEY] = user


def logout() -> None:
    """Xóa token, thông tin user và ngữ cảnh làm việc khỏi session_state."""
    st.session_state[_TOKEN_KEY] = None
    st.session_state[_USER_KEY] = None
    st.session_state.pop(_CONTEXT_KEY, None)


def get_token() -> str | None:
    """Lấy JWT access token hiện tại, None nếu chưa đăng nhập."""
    return st.session_state.get(_TOKEN_KEY)


def get_current_user() -> dict[str, Any] | None:
    """Lấy thông tin user hiện tại (dict có 'id', 'email', 'role', ...), None nếu chưa đăng nhập."""
    return st.session_state.get(_USER_KEY)


def is_logged_in() -> bool:
    """Kiểm tra đã đăng nhập hay chưa."""
    return get_token() is not None


def is_admin() -> bool:
    """Kiểm tra user hiện tại có role 'admin' hay không."""
    user = get_current_user()
    return user is not None and user.get("role") == "admin"


def set_flash(message: str, kind: str = "success") -> None:
    """Đặt thông báo hiển thị (st.toast) ở lần chạy kế tiếp, sống sót qua st.rerun()."""
    st.session_state[_FLASH_KEY] = (message, kind)


def pop_flash() -> tuple[str, str] | None:
    """Lấy và xóa thông báo đã đặt bằng set_flash, None nếu không có."""
    return st.session_state.pop(_FLASH_KEY, None)


def get_context() -> dict[str, Any]:
    """Ngữ cảnh làm việc hiện tại: project_id, dataset_id, version_id (key vắng = chưa chọn)."""
    return st.session_state.setdefault(_CONTEXT_KEY, {})


def set_context(**values: Any) -> None:
    """Cập nhật ngữ cảnh làm việc (project_id, dataset_id, version_id, ...)."""
    get_context().update(values)
