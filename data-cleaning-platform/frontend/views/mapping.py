"""Trang Mapping cột: gợi ý ánh xạ tên cột của file với schema chuẩn và chọn các cột cần đổi tên.

Backend không có endpoint lưu mapping (docs/BACKEND_TODO.md, mục 2 #4): xác nhận mapping tạo ra
các bước rule `rename_column`, lưu vào ngữ cảnh làm việc (`pending_steps`) để bước Gợi ý làm sạch
đưa vào cùng luồng xem trước -> áp dụng.
"""

from html import escape
from typing import Any

import streamlit as st

from api_client import suggest_mapping
from components.dataset_context import dataset_context_bar, load_profile
from components.mapping_logic import (
    KEEP,
    build_rename_steps,
    duplicate_names,
    parse_target_schema,
)
from components.navigation import get_page
from components.ui import (
    badge_html,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
    stepper,
)
from state import get_context, get_token, set_context, set_flash

_TARGET_KEY = "mapping_target_text"
_EXAMPLE_TARGETS = "ho_ten\nemail\nso_dien_thoai\nngay_sinh\ntuoi\ntinh_thanh"


def _fill_example() -> None:
    st.session_state[_TARGET_KEY] = _EXAMPLE_TARGETS


def _request_suggestion(version_id: int) -> None:
    targets, problems = parse_target_schema(st.session_state.get(_TARGET_KEY, ""))
    if problems:
        st.error("\n".join(f"- {p}" for p in problems), icon=":material/error:")
        return
    suggestion, error = safe_call(
        "Đang gợi ý mapping…", suggest_mapping, get_token(), version_id, targets
    )
    if error is not None:
        if error.status_code >= 500 or error.status_code == 0:
            error_state(error, key="mapping_suggest")
        else:
            st.error(error.detail, icon=":material/error:")
        return
    previous = (get_context().get("mapping") or {}).get("nonce", 0)
    set_context(
        mapping={
            "version_id": version_id,
            "targets": targets,
            "suggestion": suggestion,
            "nonce": previous + 1,
        }
    )
    st.rerun()


def _status(choice: str, source: str, suggested: str | None) -> str:
    """Nhãn trạng thái của một dòng mapping."""
    if choice == KEEP:
        return badge_html("Chưa khớp", "warning") if suggested is None else badge_html("Giữ nguyên")
    if choice == source:
        return badge_html("Đúng chuẩn", "success")
    if choice == suggested:
        return badge_html("Gợi ý", "primary")
    return badge_html("Chọn tay", "primary")


def _mapping_rows(sources: list[str], mapping: dict[str, Any]) -> list[str]:
    """Vẽ từng dòng chọn cột đích; trả danh sách lựa chọn theo thứ tự cột nguồn."""
    targets: list[str] = mapping["targets"]
    suggestion: dict[str, str | None] = mapping["suggestion"]
    options = [KEEP, *targets]
    head = st.columns([3, 3, 2])
    for column, title in zip(head, ["Cột trong file", "Đổi thành", "Trạng thái"], strict=True):
        column.caption(title)

    choices = []
    for index, source in enumerate(sources):
        suggested = suggestion.get(source)
        default = options.index(suggested) if suggested in options else 0
        name_col, choice_col, status_col = st.columns([3, 3, 2], vertical_alignment="center")
        name_col.markdown(f'<span class="dc-mono">{escape(source)}</span>', unsafe_allow_html=True)
        choice = choice_col.selectbox(
            f"Đổi tên cột {source} thành",
            options,
            index=default,
            key=f"map_{mapping['nonce']}_{index}",
            label_visibility="collapsed",
        )
        status_col.markdown(_status(choice, source, suggested), unsafe_allow_html=True)
        choices.append(choice)
    return choices


def _confirm(version_id: int, steps: list[dict[str, Any]]) -> None:
    set_context(pending_steps=steps, pending_version_id=version_id)
    set_flash(f"Đã chọn {len(steps)} bước đổi tên cột. Hãy xem trước và áp dụng ở bước này.")
    st.switch_page(get_page("suggestions").file)


page_shell("Mapping cột", "Đổi tên cột của file về schema chuẩn")
stepper("mapping")
active = dataset_context_bar()
version_id = active.version["id"]

profile, error = load_profile(version_id)
if error is not None:
    error_state(error, key="mapping_profile")
    st.stop()
sources = [c["column_name"] for c in profile["columns"]]

context = get_context()
mapping = context.get("mapping")
if mapping and mapping["version_id"] != version_id:
    set_context(mapping=None)  # phiên bản đã đổi (áp dụng/hoàn tác): gợi ý cũ không còn đúng
    mapping = None
if context.get("pending_steps") and context.get("pending_version_id") == version_id:
    st.info(
        f"Đang có {len(context['pending_steps'])} bước đổi tên cột chờ áp dụng. "
        "Xác nhận lại ở đây sẽ thay thế các bước này.",
        icon=":material/info:",
    )

with section(
    "Schema chuẩn",
    caption=(
        "Nhập tên các cột chuẩn muốn dùng (mỗi dòng một tên). "
        "Hệ thống sẽ gợi ý cột nào của file khớp với cột nào."
    ),
):
    st.text_area(
        "Danh sách cột chuẩn",
        key=_TARGET_KEY,
        height=150,
        placeholder="ho_ten\nemail\nso_dien_thoai",
    )
    suggest_col, example_col, _ = st.columns([2, 2, 4])
    if suggest_col.button(
        "Gợi ý mapping", type="primary", icon=":material/auto_fix_high:", use_container_width=True
    ):
        _request_suggestion(version_id)
    example_col.button("Điền ví dụ", on_click=_fill_example, use_container_width=True)

if mapping is None:
    st.stop()

st.subheader("Kiểm tra và chỉnh mapping")
choices = _mapping_rows(sources, mapping)

steps = build_rename_steps(sources, choices)
matched = sum(1 for s in sources if mapping["suggestion"].get(s) is not None)
for cell, (label, value) in zip(
    st.columns(3),
    [
        ("Cột trong file", str(len(sources))),
        ("Gợi ý khớp", f"{matched}/{len(sources)}"),
        ("Sẽ đổi tên", str(len(steps))),
    ],
    strict=True,
):
    with cell:
        metric_card(label, value)

duplicates = duplicate_names(sources, choices)
if duplicates:
    names = ", ".join(f"“{d}”" for d in duplicates)
    st.error(
        f"Không thể có hai cột cùng tên sau khi đổi: {names}. Hãy chỉnh lại lựa chọn.",
        icon=":material/error:",
    )
elif not steps:
    st.info("Không có cột nào cần đổi tên. Bạn có thể bỏ qua bước này.", icon=":material/info:")

confirm_col, skip_col, _ = st.columns([3, 2, 3])
if confirm_col.button(
    "Xác nhận mapping",
    type="primary",
    icon=":material/check:",
    disabled=bool(duplicates) or not steps,
    use_container_width=True,
):
    _confirm(version_id, steps)
if skip_col.button("Bỏ qua bước này", icon=":material/skip_next:", use_container_width=True):
    st.switch_page(get_page("suggestions").file)
