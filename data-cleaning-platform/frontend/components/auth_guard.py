"""Chặn truy cập trang khi chưa đăng nhập hoặc không đủ quyền."""

import streamlit as st

from state import init_state, is_admin, is_logged_in


def require_login() -> None:
    """Nếu chưa đăng nhập, hiển thị thông báo và dừng render trang (st.stop())."""
    init_state()
    if not is_logged_in():
        st.warning("Vui lòng đăng nhập để tiếp tục.")
        st.stop()


def require_admin() -> None:
    """Nếu chưa đăng nhập hoặc không phải admin, hiển thị thông báo và dừng render trang."""
    require_login()
    if not is_admin():
        st.error("Bạn không có quyền truy cập trang này. Chỉ quản trị viên được phép.")
        st.stop()
