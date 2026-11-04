"""Điểm vào frontend Streamlit: cấu hình trang, nạp CSS và dựng điều hướng theo quyền.

Các trang nằm trong views/ và được khai báo ở components/navigation.py.
Header 2 hàng dùng st.navigation(position="hidden") kết hợp st.page_link theo chuẩn Wireframe.
"""

import streamlit as st

from components.navigation import PRODUCT_NAME, build_pages
from components.theme import load_css
from state import init_state, is_admin, is_logged_in

st.set_page_config(
    page_title=PRODUCT_NAME,
    page_icon=":material/cleaning_services:",
    layout="wide",
)


def main() -> None:
    """Dựng điều hướng ẩn sidebar, nạp style rồi chạy trang đang chọn."""
    init_state()
    load_css()

    logged_in = is_logged_in()
    navigation = st.navigation(
        build_pages(logged_in, is_admin()),
        position="hidden",
    )
    navigation.run()


main()
