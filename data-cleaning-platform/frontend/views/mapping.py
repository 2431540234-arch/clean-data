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
    page_shell,
    safe_call,
    section,
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


def _mapping_rows(
    sources: list[str], samples: dict[str, str], mapping: dict[str, Any]
) -> list[str]:
    """Vẽ từng dòng chọn cột chuẩn; trả danh sách lựa chọn theo thứ tự cột nguồn."""
    targets: list[str] = mapping["targets"]
    suggestion: dict[str, str | None] = mapping["suggestion"]
    options = [KEEP, *targets]
    widths = [2.2, 2, 2.8, 1.6]
    head = st.columns(widths)
    for column, title in zip(
        head, ["Cột nguồn", "Giá trị mẫu", "Cột chuẩn", "Trạng thái"], strict=True
    ):
        column.caption(title)

    choices = []
    for index, source in enumerate(sources):
        suggested = suggestion.get(source)
        default = options.index(suggested) if suggested in options else 0
        name_col, sample_col, choice_col, status_col = st.columns(
            widths, vertical_alignment="center"
        )
        name_col.markdown(f'<span class="dc-mono">{escape(source)}</span>', unsafe_allow_html=True)
        sample_col.caption(samples.get(source, "—"))
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


page_shell(
    "Mapping cột",
    "Đưa tên cột của file về bộ tên chuẩn; các bước đổi tên được áp dụng ở bước Làm sạch",
)
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


def _result_panel(
    version_id: int,
    sources: list[str],
    samples: dict[str, str],
    mapping: dict[str, Any] | None,
) -> None:
    """Bảng "Kết quả gợi ý": chọn cột chuẩn cho từng cột nguồn rồi xác nhận."""
    if mapping is None:
        st.info(
            "Chưa có gợi ý. Nhập tên cột chuẩn ở bên trái rồi bấm “Gợi ý mapping”.",
            icon=":material/info:",
        )
        return
    matched = sum(1 for s in sources if mapping["suggestion"].get(s) is not None)
    st.markdown(
        badge_html(f"{matched} khớp", "success")
        + (
            " " + badge_html(f"{len(sources) - matched} cần xem lại", "warning")
            if matched < len(sources)
            else ""
        ),
        unsafe_allow_html=True,
    )
    choices = _mapping_rows(sources, samples, mapping)
    steps = build_rename_steps(sources, choices)
    duplicates = duplicate_names(sources, choices)
    if duplicates:
        names = ", ".join(f"“{d}”" for d in duplicates)
        st.error(
            f"Không thể có hai cột cùng tên sau khi đổi: {names}. Hãy chỉnh lại lựa chọn.",
            icon=":material/error:",
        )
    elif not steps:
        st.info("Không có cột nào cần đổi tên. Bạn có thể bỏ qua bước này.", icon=":material/info:")
    st.caption(
        f"Cột để “{KEEP}” sẽ giữ nguyên tên. "
        f"Xác nhận sẽ tạo {len(steps)} bước “Đổi tên cột” để xem trước và áp dụng ở bước Làm sạch."
    )
    reset_col, confirm_col = st.columns([1, 2])
    if reset_col.button("Đặt lại", use_container_width=True, help="Quay về gợi ý ban đầu"):
        set_context(mapping={**mapping, "nonce": mapping["nonce"] + 1})
        st.rerun()
    if confirm_col.button(
        "Xác nhận và sang bước 4",
        type="primary",
        icon=":material/check:",
        disabled=bool(duplicates) or not steps,
        use_container_width=True,
    ):
        _confirm(version_id, steps)


_, skip_col = st.columns([5, 1.6])
if skip_col.button("Bỏ qua bước này", icon=":material/skip_next:", use_container_width=True):
    st.switch_page(get_page("suggestions").file)

samples = {
    c["column_name"]: str(c["sample_values"][0]) if c["sample_values"] else "—"
    for c in profile["columns"]
}
left, right = st.columns([1, 1.9], gap="large")
with left, section("Bộ cột chuẩn"):
    st.text_area(
        "Tên cột chuẩn, mỗi dòng một tên",
        key=_TARGET_KEY,
        height=190,
        placeholder="ho_ten\nemail\nso_dien_thoai",
    )
    if st.button(
        "Gợi ý mapping",
        type="primary",
        icon=":material/auto_fix_high:",
        use_container_width=True,
    ):
        _request_suggestion(version_id)
    st.button("Điền ví dụ", on_click=_fill_example, use_container_width=True)
    st.info(
        "Gợi ý dùng từ điển đồng nghĩa tiếng Việt và so khớp gần đúng. "
        "Khi có khóa AI, các cột khó sẽ được AI gợi ý thêm.",
        icon=":material/lightbulb:",
    )
with right, section("Kết quả gợi ý"):
    _result_panel(version_id, sources, samples, mapping)
