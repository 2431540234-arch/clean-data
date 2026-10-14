"""Thẻ hiển thị một gợi ý làm sạch: giải thích lỗi + nút chấp nhận/từ chối."""

from typing import Any

import streamlit as st


def render_suggestion_card(suggestion: dict[str, Any]) -> str | None:
    """Hiển thị một gợi ý (explanation, severity, rule_json) kèm 2 nút Chấp nhận/Từ chối.

    Returns:
        "accepted" | "rejected" | None tùy nút nào được bấm.

    Gợi ý cách làm: dùng st.container với màu viền theo severity (cao=đỏ, trung bình=vàng,
    thấp=xanh), hiển thị suggestion["explanation"], expander cho rule_json chi tiết,
    2 st.button cho quyết định.
    """
    raise NotImplementedError("TODO: render thẻ gợi ý và trả về quyết định của người dùng.")
