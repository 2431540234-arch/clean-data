"""Trang Gợi ý làm sạch: duyệt gợi ý AI/quy tắc, xem trước thay đổi rồi mới áp dụng.

Luồng: sinh gợi ý -> chấp nhận/từ chối từng gợi ý -> Xem trước (bắt buộc) -> Áp dụng (có hộp thoại
xác nhận) -> tạo phiên bản mới. Các bước đổi tên cột đến từ trang Mapping (ngữ cảnh `pending_steps`)
được thêm vào cùng đợt và chạy SAU CÙNG, vì các gợi ý được sinh theo tên cột hiện tại.
"""

import json
from typing import Any

import streamlit as st

from api_client import (
    APIError,
    apply_rules,
    decide_suggestion,
    generate_suggestions,
    list_suggestions,
    preview_rules,
)
from components.dataset_context import dataset_context_bar
from components.diff_table import render_diff_table
from components.formatting import format_number
from components.labels import describe_step
from components.navigation import get_page
from components.suggestion_card import render_suggestion_card
from components.ui import (
    confirm_button,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
    stepper,
)
from state import get_context, get_token, set_context, set_flash

_FILTERS = {
    "Tất cả": None,
    "Chưa duyệt": "pending",
    "Đã chấp nhận": "accepted",
    "Đã từ chối": "rejected",
}


def _signature(steps: list[dict[str, Any]]) -> str:
    """Định danh bộ bước: xem trước chỉ có giá trị khi bộ bước không đổi kể từ lúc xem."""
    return json.dumps(steps, sort_keys=True, ensure_ascii=False)


def _show_failure(error: Any, key: str) -> None:
    """Lỗi nghiệp vụ hiện gọn tại chỗ; lỗi máy chủ/kết nối hiện đầy đủ kèm nút Thử lại."""
    if error.status_code >= 500 or error.status_code == 0:
        error_state(error, key=key)
    else:
        st.error(error.detail, icon=":material/error:")


def _generate(version_id: int) -> None:
    result, error = safe_call(
        "Đang phân tích dữ liệu và sinh gợi ý…", generate_suggestions, get_token(), version_id
    )
    if error is not None:
        _show_failure(error, "generate")
        return
    set_context(no_issues_version=None if result else version_id, preview=None)
    set_flash(
        f"Đã sinh {len(result)} gợi ý." if result else "Không phát hiện vấn đề cần làm sạch.",
        "success" if result else "info",
    )
    st.rerun()


def _decide(suggestion_id: int, decision: str) -> None:
    _, error = safe_call(
        "Đang lưu quyết định…", decide_suggestion, get_token(), suggestion_id, decision
    )
    if error is not None:
        _show_failure(error, f"decide_{suggestion_id}")
        return
    st.rerun()


def _accept_all(pending: list[dict[str, Any]]) -> None:
    with st.spinner("Đang chấp nhận các gợi ý…"):
        try:
            for item in pending:
                decide_suggestion(get_token(), item["id"], "accepted")
        except APIError as exc:
            _show_failure(exc, "accept_all")
            return
    st.rerun()


def _mapping_panel(version_id: int) -> list[dict[str, Any]]:
    """Khung các bước đổi tên cột từ trang Mapping; trả các bước sẽ được áp dụng (có thể rỗng)."""
    context = get_context()
    steps = context.get("pending_steps") or []
    if not steps or context.get("pending_version_id") != version_id:
        return []
    with section(
        "Đổi tên cột từ bước Mapping",
        caption="Các bước này chạy sau cùng, sau khi các gợi ý làm sạch được áp dụng.",
    ):
        for step in steps:
            st.markdown(f"- {describe_step(step)}")
        include = st.toggle("Áp dụng cùng đợt này", value=True, key="include_mapping")
    return steps if include else []


def _suggestion_list(suggestions: list[dict[str, Any]], version_id: int) -> None:
    counts = {
        s: sum(1 for x in suggestions if x["status"] == s)
        for s in ("pending", "accepted", "rejected")
    }
    for cell, (label, value) in zip(
        st.columns(4),
        [
            ("Tổng gợi ý", len(suggestions)),
            ("Chưa duyệt", counts["pending"]),
            ("Đã chấp nhận", counts["accepted"]),
            ("Đã từ chối", counts["rejected"]),
        ],
        strict=True,
    ):
        with cell:
            metric_card(label, format_number(value))

    chosen = st.radio(
        "Lọc gợi ý",
        list(_FILTERS),
        horizontal=True,
        key="suggestion_filter",
        label_visibility="collapsed",
    )
    bulk_col, regen_col, _ = st.columns([3, 2, 4])
    pending = [s for s in suggestions if s["status"] == "pending"]
    if bulk_col.button(
        "Chấp nhận tất cả chưa duyệt",
        icon=":material/done_all:",
        disabled=not pending,
        use_container_width=True,
    ):
        _accept_all(pending)
    with regen_col:
        if confirm_button(
            "Sinh lại gợi ý",
            key="regenerate",
            icon=":material/refresh:",
            title="Sinh lại gợi ý?",
            message="Các gợi ý hiện có và quyết định bạn đã chọn sẽ được thay bằng bộ gợi ý mới.",
            confirm_label="Sinh lại",
            warning=True,
        ):
            _generate(version_id)

    wanted = _FILTERS[chosen]
    shown = [s for s in suggestions if wanted is None or s["status"] == wanted]
    if not shown:
        st.info(f"Không có gợi ý nào ở trạng thái “{chosen}”.", icon=":material/filter_alt_off:")
    for suggestion in shown:
        decision = render_suggestion_card(suggestion)
        if decision:
            _decide(suggestion["id"], decision)


def _preview_and_apply(
    dataset: dict[str, Any], version_id: int, steps: list[dict[str, Any]]
) -> None:
    signature = _signature(steps)
    with section(
        "Xem trước và áp dụng",
        caption="Xem trước thay đổi trên mẫu dữ liệu. Chỉ áp dụng được sau khi đã xem trước.",
    ):
        st.markdown(f"**{len(steps)} bước sẽ được áp dụng:**")
        for step in steps:
            st.markdown(f"- {describe_step(step)}")

        if st.button("Xem trước", type="primary", icon=":material/preview:"):
            result, error = safe_call(
                "Đang tạo bản xem trước…", preview_rules, get_token(), version_id, steps
            )
            if error is not None:
                _show_failure(error, "preview")
            else:
                set_context(
                    preview={"signature": signature, "version_id": version_id, "result": result}
                )

        preview = get_context().get("preview")
        current = bool(
            preview and preview["signature"] == signature and preview["version_id"] == version_id
        )
        if preview and not current:
            st.info(
                "Lựa chọn đã thay đổi từ lần xem trước. Hãy bấm “Xem trước” lại để áp dụng.",
                icon=":material/info:",
            )
        if current:
            result = preview["result"]
            for cell, (label, value) in zip(
                st.columns(3),
                [
                    ("Dòng bị ảnh hưởng", format_number(result["affected_row_count"])),
                    ("Ô thay đổi", format_number(len(result["diffs"]))),
                    ("Mẫu xem trước", f"{len(result['before_rows'])} dòng"),
                ],
                strict=True,
            ):
                with cell:
                    metric_card(label, value)
            render_diff_table(result["before_rows"], result["after_rows"], result["diffs"])

        confirmed = confirm_button(
            "Áp dụng thay đổi",
            key="apply_changes",
            icon=":material/check_circle:",
            type="primary",
            disabled=not current,
            title="Áp dụng thay đổi?",
            message=(
                f"Hệ thống sẽ tạo một phiên bản mới từ {len(steps)} bước đã xem trước. "
                "Phiên bản hiện tại vẫn được giữ, bạn có thể hoàn tác ở Lịch sử phiên bản."
            ),
            confirm_label="Áp dụng",
        )
        if not current:
            st.caption("Bấm “Xem trước” để mở khóa nút áp dụng.")
    if confirmed:
        _apply(dataset, steps, preview["result"]["affected_row_count"])


def _apply(dataset: dict[str, Any], steps: list[dict[str, Any]], affected: int) -> None:
    version, error = safe_call(
        "Đang áp dụng thay đổi…", apply_rules, get_token(), dataset["id"], steps
    )
    if error is not None:
        _show_failure(error, "apply")
        return
    set_context(
        last_applied={
            "dataset_id": dataset["id"],
            "version_number": version["version_number"],
            "steps": len(steps),
            "affected": affected,
        },
        preview=None,
        pending_steps=None,
        pending_version_id=None,
        no_issues_version=None,
    )
    set_flash(f"Đã áp dụng {len(steps)} bước, tạo phiên bản {version['version_number']}.")
    st.rerun()


def _applied_banner(dataset_id: int) -> None:
    last = get_context().get("last_applied")
    if not last or last["dataset_id"] != dataset_id:
        return
    st.success(
        f"Đã áp dụng {last['steps']} bước và tạo phiên bản {last['version_number']} "
        f"({format_number(last['affected'])} dòng bị ảnh hưởng trong mẫu xem trước).",
        icon=":material/check_circle:",
    )
    history_col, export_col, close_col, _ = st.columns([3, 3, 2, 2])
    if history_col.button(
        "Xem lịch sử phiên bản", icon=":material/history:", use_container_width=True
    ):
        st.switch_page(get_page("history").file)
    if export_col.button("Xuất dữ liệu", icon=":material/download:", use_container_width=True):
        st.switch_page(get_page("export").file)
    if close_col.button("Ẩn", icon=":material/close:", use_container_width=True):
        set_context(last_applied=None)
        st.rerun()


def _empty_states(version_id: int) -> None:
    """Trạng thái rỗng: chưa sinh gợi ý, hoặc đã sinh mà dữ liệu đã sạch."""
    if get_context().get("no_issues_version") == version_id:
        empty_state(
            "task_alt",
            "Dữ liệu đã sạch",
            "Không phát hiện thêm vấn đề cần làm sạch ở phiên bản này. Bạn có thể xuất dữ liệu.",
            cta_label="Xuất dữ liệu",
            cta_page="export",
        )
        if st.button("Phân tích lại", icon=":material/refresh:"):
            _generate(version_id)
    elif empty_state(
        "auto_fix_high",
        "Chưa có gợi ý cho phiên bản này",
        "Hệ thống phân tích dữ liệu bằng quy tắc và AI rồi đề xuất các bước làm sạch. "
        "Bạn xem trước và duyệt từng gợi ý trước khi áp dụng.",
        cta_label="Sinh gợi ý",
    ):
        _generate(version_id)


page_shell("Gợi ý làm sạch", "Duyệt gợi ý, xem trước thay đổi rồi mới áp dụng")
stepper("suggestions")
active = dataset_context_bar()
dataset, version = active.dataset, active.version
version_id = version["id"]

_applied_banner(dataset["id"])
mapping_steps = _mapping_panel(version_id)

suggestions, error = safe_call("Đang tải gợi ý…", list_suggestions, get_token(), version_id)
if error is not None:
    error_state(error, key="suggestions")
    st.stop()

accepted_steps = [
    step
    for item in suggestions
    if item["status"] == "accepted"
    for step in item["proposed_rule"]["steps"]
]
all_steps = accepted_steps + mapping_steps

if not suggestions and not all_steps:
    _empty_states(version_id)
    st.stop()

tab_review, tab_apply = st.tabs(["Gợi ý", "Xem trước và áp dụng"])
with tab_review:
    if suggestions:
        _suggestion_list(suggestions, version_id)
        if all_steps:
            st.success(
                f"Đã chọn {len(all_steps)} bước. Mở tab “Xem trước và áp dụng” để kiểm tra.",
                icon=":material/arrow_forward:",
            )
    else:
        _empty_states(version_id)
with tab_apply:
    if all_steps:
        _preview_and_apply(dataset, version_id, all_steps)
    else:
        st.info(
            "Chấp nhận ít nhất một gợi ý ở tab “Gợi ý” để xem trước và áp dụng.",
            icon=":material/touch_app:",
        )
