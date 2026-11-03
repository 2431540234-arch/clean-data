"""Thẻ hiển thị một gợi ý làm sạch: giải thích lỗi + nút chấp nhận/từ chối."""

from typing import Any

import streamlit as st

from components.formatting import to_json_text
from components.labels import (
    SEVERITY_KIND,
    SOURCE_LABELS,
    STATUS_LABELS,
    describe_step,
    severity_label,
)
from components.ui import badge_html

_LOW_CONFIDENCE = 0.7  # dưới ngưỡng này thẻ gắn nhãn "Độ tin cậy thấp"
_STATUS_KIND = {"pending": "neutral", "accepted": "success", "rejected": "error"}


def render_suggestion_card(suggestion: dict[str, Any], severity: str | None = None) -> str | None:
    """Hiển thị một gợi ý (explanation, confidence, proposed_rule) kèm 2 nút Chấp nhận/Từ chối.

    severity: mức độ nghiêm trọng của lỗi gắn với gợi ý (tra từ GET /profiling/{id}/issues theo
    issue_id); có thì thẻ có viền trái màu theo mức độ và nhãn "Mức độ", không có thì thẻ như cũ.

    Returns:
        "accepted" | "rejected" | None tùy nút nào được bấm.
    """
    suggestion_id = suggestion["id"]
    status = suggestion["status"]
    steps = suggestion["proposed_rule"]["steps"]
    confidence = suggestion.get("confidence")
    title = describe_step(steps[0]) if len(steps) == 1 else f"{len(steps)} bước làm sạch"

    decision = None
    key = f"sev-{severity}-{suggestion_id}" if severity else f"sug-{suggestion_id}"
    with st.container(border=True, key=key):
        head, state = st.columns([5, 2], vertical_alignment="center")
        head.markdown(f"**{title}**")
        state.markdown(
            badge_html(STATUS_LABELS[status], _STATUS_KIND[status]), unsafe_allow_html=True
        )

        badges = [
            badge_html(SOURCE_LABELS.get(suggestion["source"], suggestion["source"]), "primary")
        ]
        if severity:
            badges.append(
                badge_html(f"Mức độ {severity_label(severity).lower()}", SEVERITY_KIND[severity])
            )
        if confidence is not None:
            badges.append(badge_html(f"Độ tin cậy {round(confidence * 100)}%"))
            if confidence < _LOW_CONFIDENCE:
                badges.append(badge_html("Độ tin cậy thấp", "warning"))
        st.markdown(" ".join(badges), unsafe_allow_html=True)

        st.write(suggestion["explanation"])
        with st.expander("Chi tiết rule (JSON)"):
            st.code(to_json_text(suggestion["proposed_rule"]), language=None)

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
