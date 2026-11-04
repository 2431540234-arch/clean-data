"""Chặn truy cập trang khi chưa đăng nhập hoặc không đủ quyền.

Đây là lớp bảo vệ thứ hai: menu đã ẩn trang admin với user thường (components.navigation),
nhưng từng trang vẫn tự kiểm tra phòng khi truy cập trực tiếp bằng URL.
"""

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from components.navigation import get_page
from state import init_state, is_admin, is_logged_in, set_flash


def require_login() -> None:
    """Đưa người chưa đăng nhập về trang đăng nhập kèm thông báo."""
    init_state()
    if not is_logged_in():
        if get_script_run_ctx(suppress_warning=True) is None:
            st.warning("Vui lòng đăng nhập để tiếp tục.", icon=":material/lock:")
            st.stop()
            return
        set_flash("Vui lòng đăng nhập để tiếp tục.", "warning")
        st.switch_page(get_page("login").file)
        st.stop()


def require_admin() -> None:
    """Nếu chưa đăng nhập hoặc không phải admin, hiển thị thông báo và dừng render trang."""
    require_login()
    if not is_admin():
        st.error(
            "Bạn không có quyền truy cập trang này. Chỉ quản trị viên được phép.",
            icon=":material/block:",
        )
        st.stop()
