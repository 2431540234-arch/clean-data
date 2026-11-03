"""Trang Làm sạch dữ liệu: duyệt gợi ý AI, quy tắc có sẵn, tự viết rule; đổ vào MỘT hàng đợi, xem trước rồi mới áp dụng.

Theo chuẩn Wireframe Khung 07:
- Cột trái: 3 Nguồn quy tắc (Gợi ý AI, Quy tắc có sẵn, Tự viết quy tắc).
- Cột phải: HÀNG ĐỢI ÁP DỤNG DUY NHẤT (có nút ↑/↓ và ✕).
- Bắt buộc Xem trước thay đổi rồi mới mở khóa nút Áp dụng; đổi hàng đợi thì phải xem trước lại.
- Bảng Diff Before/After 3 tabs: Thay đổi theo ô, Dữ liệu sau, Dữ liệu trước.
- Hộp thoại xác nhận áp dụng để tạo phiên bản mới v+1.
"""

import json
from typing import Any

import streamlit as st

from api_client import (
    APIError,
    apply_rules,
    create_rule_template,
    decide_suggestion,
    generate_suggestions,
    get_issues,
    list_rule_templates,
    list_suggestions,
    preview_rules,
)
from components.dataset_context import dataset_context_bar
from components.diff_table import render_diff_table
from components.formatting import format_number, to_json_text
from components.labels import describe_step, severity_label, SEVERITY_KIND, SOURCE_LABELS, STATUS_LABELS
from components.navigation import get_page
from components.rule_catalog import SYSTEM_RULES, get_system_rule
from components.ui import (
    badge_html,
    confirm_button,
    empty_state,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    safe_page_link,
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

_STATUS_KIND = {"pending": "neutral", "accepted": "success", "rejected": "error"}
_LOW_CONFIDENCE = 0.7

ALLOWED_OPS = [
    "trim_whitespace",
    "change_case",
    "replace_values",
    "standardize_date",
    "standardize_phone",
    "standardize_email",
    "cast_type",
    "fill_missing",
    "drop_duplicates",
    "drop_rows_where",
    "flag_outliers",
    "rename_column",
    "drop_column",
]


def _signature(steps: list[dict[str, Any]]) -> str:
    """Định danh chuỗi các bước: dùng kiểm tra tính hợp lệ của bản xem trước."""
    return json.dumps(steps, sort_keys=True, ensure_ascii=False)


def _show_failure(error: Any, key: str) -> None:
    if getattr(error, "status_code", 0) >= 500 or getattr(error, "status_code", 0) == 0:
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
    set_context(preview=None)
    st.rerun()


def _accept_all(pending: list[dict[str, Any]]) -> None:
    with st.spinner("Đang chấp nhận các gợi ý…"):
        try:
            for item in pending:
                decide_suggestion(get_token(), item["id"], "accepted")
        except APIError as exc:
            _show_failure(exc, "accept_all")
            return
    set_context(preview=None)
    st.rerun()


def _severity_by_issue(version_id: int) -> dict[int, str]:
    try:
        return {i["id"]: i["severity"] for i in get_issues(get_token(), version_id)}
    except APIError:
        return {}


def _render_custom_suggestion_card(suggestion: dict[str, Any], severity: str | None = None) -> None:
    """Thẻ gợi ý chuẩn wireframe: nhãn độ tin cậy, giải thích, xem JSON, nút chấp nhận/từ chối."""
    suggestion_id = suggestion["id"]
    status = suggestion["status"]
    steps = suggestion["proposed_rule"]["steps"]
    confidence = suggestion.get("confidence")
    title = describe_step(steps[0]) if len(steps) == 1 else f"{len(steps)} bước làm sạch"

    key = f"sev-{severity}-{suggestion_id}" if severity else f"sug-{suggestion_id}"
    with st.container(border=True, key=key):
        head, state_col = st.columns([7, 3], vertical_alignment="center")
        with head:
            st.markdown(f"**{title}**")
        with state_col:
            st.markdown(badge_html(STATUS_LABELS[status], _STATUS_KIND[status]), unsafe_allow_html=True)

        badges = [
            badge_html(SOURCE_LABELS.get(suggestion["source"], suggestion["source"]), "primary")
        ]
        if severity:
            badges.append(
                badge_html(f"Mức độ {severity_label(severity).lower()}", SEVERITY_KIND.get(severity, "neutral"))
            )
        if confidence is not None:
            pct = int(confidence * 100)
            if confidence < _LOW_CONFIDENCE:
                badges.append(badge_html(f"Độ tin cậy thấp · {pct}%", "warning"))
            else:
                badges.append(badge_html(f"Tin cậy {pct}%", "success"))

        st.markdown(" ".join(badges), unsafe_allow_html=True)

        if suggestion.get("explanation"):
            st.caption(suggestion["explanation"])

        with st.expander("Xem quy tắc JSON"):
            st.code(to_json_text(suggestion["proposed_rule"]), language="json")

        act_col1, act_col2, _ = st.columns([3, 3, 4])
        with act_col1:
            if st.button(
                "Chấp nhận",
                key=f"accept_{suggestion_id}",
                type="primary",
                disabled=(status == "accepted"),
                use_container_width=True,
            ):
                _decide(suggestion_id, "accepted")
        with act_col2:
            if status == "rejected":
                if st.button("Hoàn tác từ chối", key=f"reject_{suggestion_id}", use_container_width=True):
                    _decide(suggestion_id, "pending")
            else:
                if st.button("Từ chối", key=f"reject_{suggestion_id}", use_container_width=True):
                    _decide(suggestion_id, "rejected")


def _render_source_available_rules(project_id: int | None, available_cols: list[str]) -> None:
    sub_tab_sys, sub_tab_proj = st.tabs(["Hệ thống (13)", "Quy tắc của dự án"])
    context = get_context()

    with sub_tab_sys:
        st.caption("Chọn quy tắc và cột áp dụng để đưa vào hàng đợi.")
        selected_sys_id = st.selectbox(
            "Chọn quy tắc hệ thống",
            options=[r.id for r in SYSTEM_RULES],
            format_func=lambda rid: f"{get_system_rule(rid).name} ({get_system_rule(rid).category})",
            key="sys_rule_select",
        )
        sys_rule = get_system_rule(selected_sys_id)
        if sys_rule:
            st.markdown(f"*{sys_rule.description}*")
            target_col = None
            if sys_rule.requires_column:
                target_col = st.selectbox(
                    "Cột áp dụng",
                    options=["*text"] + available_cols if available_cols else ["*text"],
                    key="sys_rule_col",
                )
            if st.button("+ Thêm vào hàng đợi", key=f"btn_add_sys_{sys_rule.id}", type="primary"):
                step_obj = {"op": sys_rule.op, "params": dict(sys_rule.default_params)}
                if target_col:
                    step_obj["column"] = target_col
                
                queue = context.get("rule_queue") or []
                queue.append(step_obj)
                set_context(rule_queue=queue, preview=None)
                set_flash(f"Đã thêm '{sys_rule.name}' vào hàng đợi.", "success")
                st.rerun()

    with sub_tab_proj:
        if not project_id:
            st.info("Vui lòng chọn Dự án ở thanh menu trên cùng.", icon=":material/info:")
        else:
            token = get_token()
            templates = []
            if token:
                try:
                    templates = list_rule_templates(token, project_id)
                except Exception:
                    templates = []
            
            if not templates:
                st.caption("Chưa có quy tắc nào được lưu trong dự án này.")
            else:
                for tmpl in templates:
                    with st.container(border=True):
                        c1, c2 = st.columns([7, 3])
                        with c1:
                            st.markdown(f"**{tmpl['name']}**")
                            st.caption(f"{len(tmpl.get('rules', {}).get('steps', []))} bước")
                        with c2:
                            if st.button("Thêm", key=f"add_tmpl_to_q_{tmpl['id']}", use_container_width=True):
                                tmpl_steps = tmpl.get("rules", {}).get("steps", [])
                                queue = context.get("rule_queue") or []
                                queue.extend(tmpl_steps)
                                set_context(rule_queue=queue, preview=None)
                                set_flash(f"Đã thêm {len(tmpl_steps)} bước của '{tmpl['name']}' vào hàng đợi.", "success")
                                st.rerun()

        safe_page_link(get_page("rule_library").file, label="Mở Thư viện quy tắc đầy đủ →", icon=":material/open_in_new:")


def _render_source_custom_rule(project_id: int | None, available_cols: list[str]) -> None:
    st.caption("Tự định nghĩa một phép biến đổi theo chuẩn docs/rule_dsl.md.")
    c1, c2 = st.columns(2)
    with c1:
        chosen_op = st.selectbox("Phép biến đổi", ALLOWED_OPS, key="custom_rule_op")
    with c2:
        chosen_col = st.selectbox("Cột áp dụng", ["*text"] + available_cols if available_cols else ["*text"], key="custom_rule_col")

    params_json_str = st.text_input("Tham số (JSON)", value="{}", key="custom_rule_params")
    
    parsed_params = {}
    try:
        parsed_params = json.loads(params_json_str) if params_json_str.strip() else {}
    except Exception:
        st.caption("⚠️ Tham số JSON chưa đúng cú pháp, sẽ dùng rỗng {}.")

    preview_step = {"op": chosen_op, "column": chosen_col, "params": parsed_params}
    with st.expander("Xem trước cấu trúc JSON"):
        st.code(json.dumps(preview_step, indent=2, ensure_ascii=False), language="json")

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("+ Thêm vào hàng đợi", key="btn_add_custom_step", type="primary", use_container_width=True):
            context = get_context()
            queue = context.get("rule_queue") or []
            queue.append(preview_step)
            set_context(rule_queue=queue, preview=None)
            set_flash("Đã thêm quy tắc tùy chỉnh vào hàng đợi.", "success")
            st.rerun()
    with btn2:
        if st.button("Lưu vào dự án", key="btn_save_custom_step", use_container_width=True):
            if not project_id:
                st.error("Vui lòng chọn Dự án.")
            else:
                try:
                    create_rule_template(
                        get_token(),
                        project_id,
                        name=f"Quy tắc {chosen_op} trên {chosen_col}",
                        rules={"steps": [preview_step]},
                    )
                    set_flash("Đã lưu quy tắc vào dự án.", "success")
                    st.rerun()
                except APIError as exc:
                    st.error(exc.detail)


def _render_applied_banner(dataset_id: int) -> None:
    last = get_context().get("last_applied")
    if not last or last.get("dataset_id") != dataset_id:
        return
    st.success(
        f"Đã áp dụng {last['steps']} bước và tạo phiên bản {last['version_number']} "
        f"({format_number(last['affected'])} dòng bị ảnh hưởng trong mẫu xem trước).",
        icon=":material/check_circle:",
    )
    c1, c2, c3, _ = st.columns([3, 3, 2, 2])
    with c1:
        if st.button("Xem lịch sử phiên bản", icon=":material/history:", use_container_width=True):
            st.switch_page(get_page("history").file)
    with c2:
        if st.button("Xuất dữ liệu", icon=":material/download:", use_container_width=True):
            st.switch_page(get_page("export").file)
    with c3:
        if st.button("Ẩn", icon=":material/close:", use_container_width=True):
            set_context(last_applied=None)
            st.rerun()


# --- ĐIỂM VÀO VIEW CHÍNH ---

page_shell("Gợi ý làm sạch", "Duyệt gợi ý, xem trước thay đổi rồi mới áp dụng", page_key="suggestions")
stepper("suggestions")

active = dataset_context_bar()
dataset, version = active.dataset, active.version
version_id = version["id"]
project_id = dataset.get("project_id")

_render_applied_banner(dataset["id"])

available_cols = []
if version.get("schema_profile"):
    available_cols = [c["column_name"] for c in version["schema_profile"].get("columns", [])]

context = get_context()
mapping_steps = []
if context.get("pending_version_id") == version_id and context.get("pending_steps"):
    mapping_steps = context.get("pending_steps")

suggestions, error = safe_call("Đang tải gợi ý…", list_suggestions, get_token(), version_id)
if error is not None:
    error_state(error, key="suggestions_err")
    st.stop()

# Kiểm tra trạng thái rỗng
if not suggestions and not context.get("rule_queue") and not mapping_steps:
    if context.get("no_issues_version") == version_id:
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
        "Hệ thống phân tích dữ liệu bằng quy tắc và AI rồi đề xuất các bước làm sạch. Bạn xem trước và duyệt từng gợi ý trước khi áp dụng.",
        cta_label="Sinh gợi ý",
    ):
        _generate(version_id)
    st.stop()

manual_queue: list[dict[str, Any]] = context.get("rule_queue") or []
accepted_ai_steps: list[dict[str, Any]] = [
    step
    for item in (suggestions or [])
    if item["status"] == "accepted"
    for step in item["proposed_rule"]["steps"]
]
combined_queue = accepted_ai_steps + manual_queue

# BỐ CỤC 2 CỘT CHUẨN WIREFRAME KHUNG 07
left_col, right_col = st.columns([5, 5], gap="large")

# ==================== CỘT TRÁI: 3 NGUỒN QUY TẮC ====================
with left_col:
    st.markdown("### 📥 Nguồn quy tắc")
    source_tab_ai, source_tab_lib, source_tab_custom = st.tabs([
        f"Gợi ý AI ({len(suggestions) if suggestions else 0})",
        "Quy tắc có sẵn",
        "Tự viết quy tắc",
    ])

    with source_tab_ai:
        if not suggestions:
            if empty_state(
                "auto_fix_high",
                "Chưa có gợi ý cho phiên bản này",
                "Hệ thống phân tích dữ liệu bằng quy tắc và AI rồi đề xuất các bước làm sạch.",
                cta_label="Sinh gợi ý",
            ):
                _generate(version_id)
        else:
            severities = _severity_by_issue(version_id)
            counts = {
                s: sum(1 for x in suggestions if x["status"] == s)
                for s in ("pending", "accepted", "rejected")
            }

            # 4 Thẻ chỉ số gợi ý chuẩn Wireframe
            for cell, (label, value) in zip(
                st.columns(4),
                [
                    ("Tổng gợi ý", str(len(suggestions))),
                    ("Chưa duyệt", str(counts["pending"])),
                    ("Đã chấp nhận", str(counts["accepted"])),
                    ("Đã từ chối", str(counts["rejected"])),
                ],
                strict=True,
            ):
                with cell:
                    metric_card(label, value)

            chosen_filter = st.radio(
                "Lọc trạng thái gợi ý",
                list(_FILTERS.keys()),
                horizontal=True,
                key="suggestion_filter",
                label_visibility="collapsed",
            )

            pending_items = [s for s in suggestions if s["status"] == "pending"]
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                if st.button("Chấp nhận tất cả chưa duyệt", icon=":material/done_all:", disabled=not pending_items, use_container_width=True):
                    _accept_all(pending_items)
            with b_col2:
                if confirm_button(
                    "Sinh lại gợi ý",
                    key="regenerate",
                    icon=":material/refresh:",
                    title="Sinh lại gợi ý AI?",
                    message="Toàn bộ gợi ý hiện có sẽ được phân tích và sinh lại từ đầu.",
                    confirm_label="Sinh lại",
                    warning=True,
                ):
                    _generate(version_id)

            wanted_status = _FILTERS[chosen_filter]
            filtered_sugs = [s for s in suggestions if wanted_status is None or s["status"] == wanted_status]

            if not filtered_sugs:
                st.info(f"Không có gợi ý nào ở trạng thái “{chosen_filter}”.", icon=":material/filter_alt_off:")
            else:
                for sug in filtered_sugs:
                    _render_custom_suggestion_card(sug, severities.get(sug.get("issue_id")))

    with source_tab_lib:
        _render_source_available_rules(project_id, available_cols)

    with source_tab_custom:
        _render_source_custom_rule(project_id, available_cols)


# ==================== CỘT PHẢI: HÀNG ĐỢI ÁP DỤNG & XEM TRƯỚC ====================
with right_col:
    st.markdown("### 📋 Hàng đợi áp dụng")

    include_mapping = False
    if mapping_steps:
        with section(
            "Đổi tên cột từ bước Mapping",
            caption="Các bước này chạy sau cùng, sau khi các gợi ý làm sạch được áp dụng.",
        ):
            for step in mapping_steps:
                st.markdown(f"- {describe_step(step)}")
            include_mapping = st.toggle("Áp dụng cùng đợt này", value=True, key="include_mapping")

    final_execution_steps = list(combined_queue)
    if include_mapping and mapping_steps:
        final_execution_steps.extend(mapping_steps)

    signature = _signature(final_execution_steps)

    if not final_execution_steps:
        st.info(
            "Chấp nhận ít nhất một gợi ý ở tab “Gợi ý AI” để xem trước và áp dụng.",
            icon=":material/touch_app:",
        )
    else:
        st.caption(f"Đang có {len(combined_queue)} bước chính (+ {len(mapping_steps) if include_mapping else 0} bước đổi tên). Chạy từ trên xuống.")

        for idx, step in enumerate(combined_queue):
            with st.container(border=True):
                q1, q2, q3 = st.columns([1, 7, 2], vertical_alignment="center")
                with q1:
                    st.markdown(f"**{idx + 1}**")
                with q2:
                    st.markdown(f"**{describe_step(step)}**")
                    st.caption(f"op: `{step.get('op')}`")
                with q3:
                    up_dis = (idx == 0)
                    down_dis = (idx == len(combined_queue) - 1)
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        if st.button("↑", key=f"q_up_{idx}", disabled=up_dis, help="Đổi thứ tự lên"):
                            combined_queue[idx], combined_queue[idx - 1] = combined_queue[idx - 1], combined_queue[idx]
                            set_context(rule_queue=manual_queue, preview=None)
                            st.rerun()
                    with m2:
                        if st.button("↓", key=f"q_down_{idx}", disabled=down_dis, help="Đổi thứ tự xuống"):
                            combined_queue[idx], combined_queue[idx + 1] = combined_queue[idx + 1], combined_queue[idx]
                            set_context(rule_queue=manual_queue, preview=None)
                            st.rerun()
                    with m3:
                        if st.button("✕", key=f"q_del_{idx}", help="Xóa khỏi hàng đợi"):
                            if step in manual_queue:
                                manual_queue.remove(step)
                                set_context(rule_queue=manual_queue, preview=None)
                            else:
                                for sug in suggestions:
                                    if step in sug["proposed_rule"]["steps"] and sug["status"] == "accepted":
                                        _decide(sug["id"], "pending")
                                        break
                            set_context(preview=None)
                            st.rerun()

    # Nút Xem trước thay đổi
    if final_execution_steps:
        st.markdown("")
        if st.button("Xem trước", type="primary", icon=":material/preview:", use_container_width=True):
            result, error = safe_call(
                "Đang tạo bản xem trước…",
                preview_rules,
                get_token(),
                version_id,
                final_execution_steps,
            )
            if error is not None:
                _show_failure(error, "preview")
            else:
                set_context(
                    preview={"signature": signature, "version_id": version_id, "result": result}
                )
                set_flash("Đã tạo bản xem trước thành công!", "success")
                st.rerun()

    preview_data = context.get("preview")
    is_preview_valid = bool(
        preview_data
        and preview_data.get("signature") == signature
        and preview_data.get("version_id") == version_id
        and final_execution_steps
    )

    if preview_data and not is_preview_valid and final_execution_steps:
        st.info("Lựa chọn đã thay đổi từ lần xem trước. Hãy bấm “Xem trước” lại để áp dụng.", icon=":material/info:")

    if is_preview_valid:
        res = preview_data["result"]
        st.markdown("---")
        st.markdown("#### 🔍 Kết quả xem trước")

        m_c1, m_c2, m_c3 = st.columns(3)
        with m_c1:
            metric_card("Dòng bị ảnh hưởng", format_number(res.get("affected_row_count", 0)))
        with m_c2:
            metric_card("Ô thay đổi", format_number(len(res.get("diffs", []))))
        with m_c3:
            metric_card("Mẫu xem trước", f"{len(res.get('before_rows', []))} dòng")

        render_diff_table(res.get("before_rows", []), res.get("after_rows", []), res.get("diffs", []))

    st.markdown("")
    apply_confirmed = confirm_button(
        "Áp dụng thay đổi",
        key="apply_changes",
        icon=":material/check_circle:",
        type="primary",
        disabled=not is_preview_valid,
        title="Áp dụng thay đổi?",
        message=(
            f"Hệ thống sẽ tạo một phiên bản mới từ {len(final_execution_steps)} bước đã xem trước. "
            f"Phiên bản hiện tại vẫn được giữ, bạn có thể hoàn tác ở Lịch sử phiên bản."
        ),
        confirm_label="Áp dụng",
    )

    if not is_preview_valid and final_execution_steps:
        st.caption("Bấm “Xem trước” để mở khóa nút áp dụng.")

    if apply_confirmed:
        with st.spinner("Đang áp dụng thay đổi…"):
            v_res, a_err = safe_call(
                "Đang áp dụng thay đổi…",
                apply_rules,
                get_token(),
                dataset["id"],
                final_execution_steps,
            )
            if a_err is not None:
                _show_failure(a_err, "apply")
            else:
                set_context(
                    last_applied={
                        "dataset_id": dataset["id"],
                        "version_number": v_res["version_number"],
                        "steps": len(final_execution_steps),
                        "affected": preview_data["result"].get("affected_row_count", 0) if preview_data else 0,
                    },
                    preview=None,
                    rule_queue=[],
                    pending_steps=None,
                    pending_version_id=None,
                    no_issues_version=None,
                )
                set_flash(f"Đã áp dụng {len(final_execution_steps)} bước, tạo phiên bản {v_res['version_number']}.")
                st.rerun()
