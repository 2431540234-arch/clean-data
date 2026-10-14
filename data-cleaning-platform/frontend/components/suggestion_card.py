"""Thẻ hiển thị một gợi ý làm sạch: giải thích lỗi + nút chấp nhận/từ chối."""

from typing import Any

import streamlit as st


def render_suggestion_card(suggestion: dict[str, Any]) -> str | None:
    """Hiển thị một gợi ý (explanation, confidence, proposed_rule) kèm 2 nút Chấp nhận/Từ chối.

    Returns:
        "accepted" | "rejected" | None tùy nút nào được bấm.

    Gợi ý cách làm: dùng st.container, hiển thị suggestion["explanation"] và độ tin cậy
    suggestion["confidence"], expander cho suggestion["proposed_rule"] chi tiết (màu viền theo
    mức độ nghiêm trọng của lỗi gắn qua issue_id, nếu có), 2 st.button cho quyết định.
    """
    raise NotImplementedError("TODO: render thẻ gợi ý và trả về quyết định của người dùng.")
