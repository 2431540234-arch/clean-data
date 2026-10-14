"""Sidebar chung: hiển thị thông tin user đang đăng nhập, ẩn menu admin với user thường."""

import streamlit as st


def render_sidebar() -> None:
    """Hiển thị thông tin user hiện tại và nút đăng xuất ở sidebar.

    Gợi ý cách làm: dùng state.get_current_user() để hiển thị email/role; nếu
    state.is_admin() thì hiển thị thêm liên kết tới các trang quản trị (10, 11);
    nút đăng xuất gọi state.logout() rồi st.rerun().
    """
    raise NotImplementedError("TODO: render thông tin user + menu điều hướng theo role.")
