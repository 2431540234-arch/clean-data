"""Thẻ hiển thị một gợi ý làm sạch: giải thích lỗi + nút chấp nhận/từ chối."""

from typing import Any

import streamlit as st

from components.labels import SOURCE_LABELS, STATUS_LABELS, describe_step
from components.ui import badge_html

_LOW_CONFIDENCE = 0.7  # dưới ngưỡng này thẻ gắn nhãn "Độ tin cậy thấp"
_STATUS_KIND = {"pending": "neutral", "accepted": "success", "rejected": "error"}


def render_suggestion_card(suggestion: dict[str, Any]) -> str | None:
    """Hiển thị một gợi ý (explanation, confidence, proposed_rule) kèm 2 nút Chấp nhận/Từ chối.

    Mức độ nghiêm trọng của lỗi (gắn qua issue_id) chưa có endpoint để tra (docs/BACKEND_TODO.md,
    mục 2 #2) nên thẻ chưa tô màu theo mức độ.

    Returns:
        "accepted" | "rejected" | None tùy nút nào được bấm.
    """
    suggestion_id = suggestion["id"]
    status = suggestion["status"]
    steps = suggestion["proposed_rule"]["steps"]
    confidence = suggestion.get("confidence")
    title = describe_step(steps[0]) if len(steps) == 1 else f"{len(steps)} bước làm sạch"

    decision = None
    with st.container(border=True):
        head, state = st.columns([5, 2], vertical_alignment="center")
        head.markdown(f"**{title}**")
        state.markdown(
            badge_html(STATUS_LABELS[status], _STATUS_KIND[status]), unsafe_allow_html=True
        )

        badges = [
            badge_html(SOURCE_LABELS.get(suggestion["source"], suggestion["source"]), "primary")
        ]
        if confidence is not None:
            badges.append(badge_html(f"Độ tin cậy {round(confidence * 100)}%"))
            if confidence < _LOW_CONFIDENCE:
                badges.append(badge_html("Độ tin cậy thấp", "warning"))
        st.markdown(" ".join(badges), unsafe_allow_html=True)

        st.write(suggestion["explanation"])
        with st.expander("Chi tiết rule (JSON)"):
            st.json(suggestion["proposed_rule"])

        accept_col, reject_col, _ = st.columns([2, 2, 4])
        if accept_col.button(
            "Chấp nhận",
            key=f"accept_{suggestion_id}",
            icon=":material/check:",
            type="secondary" if status == "accepted" else "primary",
            disabled=status == "accepted",
            use_container_width=True,
        ):
            decision = "accepted"
        if reject_col.button(
            "Từ chối",
            key=f"reject_{suggestion_id}",
            icon=":material/close:",
            disabled=status == "rejected",
            use_container_width=True,
        ):
            decision = "rejected"
    return decision
