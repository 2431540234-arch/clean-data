"""Điểm vào frontend Streamlit: cấu hình trang, nạp CSS và dựng điều hướng theo quyền.

Các trang nằm trong views/ và được khai báo ở components/navigation.py. Chưa đăng nhập chỉ
thấy trang Đăng nhập (không có menu); đã đăng nhập thấy menu nhóm theo luồng nghiệp vụ,
mục Quản trị chỉ hiện với admin.
"""

import streamlit as st

from components.navigation import PRODUCT_NAME, build_pages
from components.sidebar import render_sidebar
from components.theme import ASSETS_DIR, load_css
from state import init_state, is_admin, is_logged_in

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon=":material/cleaning_services:",
    layout="wide",
)


def main() -> None:
    """Dựng điều hướng, sidebar rồi chạy trang đang chọn."""
    init_state()
    load_css()

    logged_in = is_logged_in()
    navigation = st.navigation(
        build_pages(logged_in, is_admin()),
        position="sidebar" if logged_in else "hidden",
    )
    if logged_in:
        st.logo(
            str(ASSETS_DIR / "logo.svg"),
            icon_image=str(ASSETS_DIR / "logo-mark.svg"),
            size="large",
        )
        render_sidebar()
    navigation.run()


main()
