"""Nạp CSS dùng chung (assets/styles.css) vào trang."""

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).resolve().parent.parent / "assets" / "styles.css"
ASSETS_DIR = _CSS_PATH.parent


def load_css() -> None:
    """Tiêm styles.css vào trang. Gọi một lần ở app.py trong mỗi lần chạy."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
