"""Trang chính của frontend Streamlit: kiểm tra đăng nhập và điều hướng tới các trang chức năng."""

import streamlit as st

from state import get_current_user, init_state, is_logged_in

st.set_page_config(page_title="Data Cleaning Platform", page_icon="🧹", layout="wide")


def main() -> None:
    """Hiển thị trang chủ: nếu chưa đăng nhập hướng dẫn qua trang Đăng nhập, nếu đã đăng
    nhập thì hiển thị lời chào và danh sách trang chức năng ở sidebar (do Streamlit tự
    sinh từ thư mục pages/).
    """
    init_state()

    st.title("🧹 Data Cleaning Platform")
    st.caption("Nền tảng làm sạch dữ liệu Excel/CSV có AI gợi ý chuẩn hóa")

    if not is_logged_in():
        st.info("Vui lòng vào trang **0. Đăng nhập** ở sidebar để tiếp tục.")
        return

    user = get_current_user()
    st.success(f"Xin chào, {user.get('full_name', user.get('email'))}!")
    st.write(
        "Sử dụng menu ở sidebar để: upload dữ liệu, xem tổng quan, nhận gợi ý làm sạch, "
        "xem lịch sử phiên bản và xuất dữ liệu."
    )


if __name__ == "__main__":
    main()
