"""Trang đăng nhập và đăng ký tài khoản."""

import streamlit as st

from api_client import APIError, get_me, login, register
from components.ui import page_shell
from state import set_logged_in

page_shell("Đăng nhập / Đăng ký", public=True)

tab_login, tab_register = st.tabs(["Đăng nhập", "Đăng ký"])

with tab_login:
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Mật khẩu", type="password")
        submitted = st.form_submit_button("Đăng nhập")

    if submitted:
        try:
            token_data = login(email, password)
            token = token_data["access_token"]
            user = get_me(token)
            set_logged_in(token, user)
            st.rerun()
        except APIError as exc:
            st.error(f"Đăng nhập thất bại: {exc.detail}")

with tab_register:
    with st.form("register_form"):
        reg_full_name = st.text_input("Họ và tên")
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input("Mật khẩu", type="password", key="reg_password")
        reg_submitted = st.form_submit_button("Đăng ký")

    if reg_submitted:
        try:
            token_data = register(reg_email, reg_password, reg_full_name)
            token = token_data["access_token"]
            user = get_me(token)
            set_logged_in(token, user)
            st.rerun()
        except APIError as exc:
            st.error(f"Đăng ký thất bại: {exc.detail}")
