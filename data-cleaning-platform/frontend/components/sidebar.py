"""Sidebar chung: thẻ người dùng, nhãn nguồn dữ liệu và nút đăng xuất."""

from html import escape

import streamlit as st

from api_client import data_source_label
from components.ui import badge_html
from state import get_current_user, is_admin, logout, set_flash


def render_sidebar() -> None:
    """Vẽ phần dưới menu ở sidebar: nhãn dữ liệu mẫu (nếu có), thẻ user và nút Đăng xuất."""
    user = get_current_user() or {}
    name = str(user.get("full_name") or user.get("email") or "Người dùng")
    email = str(user.get("email") or "")
    role = (
        badge_html("Quản trị viên", "primary")
        if is_admin()
        else badge_html("Người dùng", "neutral")
    )
    label = data_source_label()

    with st.sidebar:
        if label:
            st.markdown(
                f'<div class="dc-mock-banner" role="status">{escape(label)}'
                "<span>Dữ liệu hiển thị không phải dữ liệu thật.</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="dc-user-card">'
            f'<div class="dc-user-card__avatar" aria-hidden="true">{escape(name[:1].upper())}</div>'
            '<div class="dc-user-card__body">'
            f'<div class="dc-user-card__name">{escape(name)}</div>'
            f'<div class="dc-user-card__email">{escape(email)}</div>'
            f"{role}</div></div>",
            unsafe_allow_html=True,
        )
        if st.button("Đăng xuất", icon=":material/logout:", use_container_width=True):
            logout()
            set_flash("Bạn đã đăng xuất.", "info")
            st.rerun()
