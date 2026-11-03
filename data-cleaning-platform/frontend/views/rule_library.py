"""Trang Thư viện quy tắc: quản lý quy tắc hệ thống và quy tắc của dự án, trình soạn rule nhiều bước.

Theo đúng chuẩn Wireframe Khung 08 và yêu cầu:
- 13 quy tắc hệ thống chia theo 4 nhóm từ components/rule_catalog.py.
- Tab "Quy tắc của dự án" (lấy từ GET /api/v1/rules/by-project/{project_id}).
- Nút "Mở để sửa": nạp quy tắc vào trình soạn.
- "Lưu" luôn tạo quy tắc MỚI (POST /rules) kèm ghi chú: "Bản cũ vẫn được giữ, xóa nếu không cần."
- Trình soạn quy tắc có 2 chế độ Biểu mẫu (Form) và JSON, kiểm tra hợp lệ, xuất/nhập JSON.
"""

import json
from typing import Any

import streamlit as st

from api_client import (
    APIError,
    create_rule_template,
    delete_rule_template,
    get_dataset,
    list_projects,
    list_rule_templates,
    preview_rules,
)
from components.dataset_context import dataset_context_bar
from components.navigation import get_page
from components.rule_catalog import (
    SYSTEM_RULE_CATEGORIES,
    SYSTEM_RULES,
    get_system_rule,
)
from components.ui import (
    confirm_button,
    empty_state,
    error_state,
    page_shell,
    safe_call,
    section,
)
from state import get_context, get_token, set_context, set_flash

# Danh sách các op cho phép theo docs/rule_dsl.md
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


def _init_builder_state() -> None:
    """Khởi tạo state cho trình soạn quy tắc nếu chưa có."""
    if "rule_builder_name" not in st.session_state:
        st.session_state["rule_builder_name"] = "Quy tắc làm sạch mới"
    if "rule_builder_desc" not in st.session_state:
        st.session_state["rule_builder_desc"] = ""
    if "rule_builder_steps" not in st.session_state:
        st.session_state["rule_builder_steps"] = [
            {"op": "trim_whitespace", "column": "ho_ten", "params": {}},
            {"op": "standardize_phone", "column": "so_dien_thoai", "params": {"region": "VN", "output_format": "national"}},
        ]


def _validate_rule_set(rule_set: dict[str, Any], available_columns: list[str] | None = None) -> tuple[bool, list[str]]:
    """Kiểm tra tính hợp lệ của RuleSet theo docs/rule_dsl.md."""
    errors = []
    warnings = []
    
    steps = rule_set.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        return False, ["Quy tắc phải có ít nhất 1 bước xử lý."]

    for idx, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            errors.append(f"Bước {idx}: Cấu trúc không phải đối tượng JSON hợp lệ.")
            continue
        op = step.get("op")
        if not op or op not in ALLOWED_OPS:
            errors.append(f"Bước {idx}: Phép biến đổi '{op}' không nằm trong danh sách hỗ trợ của rule_dsl.md.")
            continue
        
        col = step.get("column")
        # drop_duplicates không bắt buộc cột
        if op != "drop_duplicates" and not col:
            errors.append(f"Bước {idx} ({op}): Bắt buộc phải chỉ định tên cột.")
        
        if available_columns and col and col != "*text" and col not in available_columns:
            warnings.append(f"Bước {idx}: Cột '{col}' không tồn tại trong dataset hiện tại.")

    is_valid = len(errors) == 0
    all_msgs = errors + warnings
    return is_valid, all_msgs


def render_rule_library_view() -> None:
    page_shell("Thư viện quy tắc", "Dùng quy tắc có sẵn của hệ thống, hoặc tự viết bộ quy tắc gồm nhiều bước để dùng lại cho nhiều dataset.", page_key="rule_library")
    _init_builder_state()

    context = get_context()
    project_id = context.get("project_id")
    token = get_token()

    # Thanh ngữ cảnh dataset nếu có
    active_dataset = None
    available_cols = []
    dataset_id = context.get("dataset_id")
    if dataset_id and token:
        try:
            active_dataset = get_dataset(token, dataset_id)
            # Lấy tên cột từ schema_profile nếu có
            if active_dataset and active_dataset.get("current_version", {}).get("schema_profile"):
                available_cols = [c["column_name"] for c in active_dataset["current_version"]["schema_profile"].get("columns", [])]
        except Exception:
            active_dataset = None

    # Nút Import JSON / Thao tác đầu trang
    header_col1, header_col2 = st.columns([8, 2])
    with header_col2:
        with st.popover("Nhập JSON", icon=":material/upload_file:"):
            st.caption("Nhập file JSON RuleSet theo chuẩn rule_dsl.md")
            uploaded_json = st.file_uploader("Chọn file JSON", type=["json"], key="import_ruleset_file")
            if uploaded_json is not None:
                try:
                    imported_data = json.load(uploaded_json)
                    if isinstance(imported_data, dict) and "steps" in imported_data:
                        st.session_state["rule_builder_name"] = imported_data.get("name", "Quy tắc nhập từ JSON")
                        st.session_state["rule_builder_desc"] = imported_data.get("description", "")
                        st.session_state["rule_builder_steps"] = imported_data.get("steps", [])
                        st.success("Đã nạp bộ quy tắc vào Trình soạn bên dưới!")
                        st.rerun()
                    else:
                        st.error("File JSON không chứa khóa 'steps' hợp lệ.")
                except Exception as e:
                    st.error(f"Lỗi đọc file JSON: {e}")

    # Hai tabs chính: Quy tắc hệ thống & Quy tắc của dự án
    tab_system, tab_project = st.tabs(["Quy tắc hệ thống (13)", "Quy tắc của dự án"])

    # --- TAB 1: QUY TẮC HỆ THỐNG ---
    with tab_system:
        st.caption("13 quy tắc tiêu chuẩn phân theo 4 nhóm chức năng. Bấm 'Dùng' để thêm vào hàng đợi áp dụng của dataset hiện tại.")
        for cat in SYSTEM_RULE_CATEGORIES:
            st.markdown(f"#### 🏷️ {cat}")
            cat_rules = [r for r in SYSTEM_RULES if r.category == cat]
            
            # Hiển thị dạng lưới 2 cột
            cols = st.columns(2)
            for idx, r in enumerate(cat_rules):
                col = cols[idx % 2]
                with col:
                    with st.container(border=True):
                        c1, c2 = st.columns([8, 2])
                        with c1:
                            st.markdown(f"**:material/{r.icon}: {r.name}**")
                            st.caption(r.description)
                            st.code(f"op: {r.op}", language="text")
                        with c2:
                            if st.button("Dùng", key=f"use_sys_{r.id}", type="secondary", use_container_width=True):
                                # Thêm vào pending_steps và chuyển sang trang Làm sạch
                                step_dict = {"op": r.op, "params": dict(r.default_params)}
                                if r.requires_column:
                                    step_dict["column"] = available_cols[0] if available_cols else "cot_du_lieu"
                                
                                queue = context.get("rule_queue") or []
                                queue.append(step_dict)
                                set_context(rule_queue=queue)
                                set_flash(f"Đã thêm bước '{r.name}' vào hàng đợi làm sạch.", "success")
                                st.switch_page(get_page("suggestions").file)

    # --- TAB 2: QUY TẮC CỦA DỰ ÁN ---
    with tab_project:
        if not project_id:
            st.info("Vui lòng chọn một Dự án ở thanh menu trên cùng để xem các quy tắc của dự án.", icon=":material/info:")
        else:
            templates = []
            if token:
                try:
                    templates = list_rule_templates(token, project_id)
                except APIError as exc:
                    error_state(exc, key="load_rule_templates")

            if not templates:
                empty_state(
                    "library_books",
                    "Chưa có quy tắc nào trong dự án này",
                    "Bạn có thể tự soạn một bộ quy tắc nhiều bước ở bên dưới và bấm 'Lưu quy tắc' để dùng lại nhiều lần.",
                )
            else:
                st.caption(f"Đang hiển thị {len(templates)} bộ quy tắc đã lưu trong dự án hiện tại.")
                for tmpl in templates:
                    with st.container(border=True):
                        tc1, tc2 = st.columns([7, 3])
                        with tc1:
                            st.markdown(f"**📋 {tmpl['name']}**")
                            if tmpl.get("description"):
                                st.caption(tmpl["description"])
                            steps_count = len(tmpl.get("rules", {}).get("steps", []))
                            st.markdown(f"*Gồm {steps_count} bước xử lý* · *Tạo: {tmpl.get('created_at', '')[:10]}*")
                        with tc2:
                            btn_c1, btn_c2, btn_c3 = st.columns(3)
                            with btn_c1:
                                if st.button("Dùng", key=f"apply_tmpl_{tmpl['id']}", type="primary", use_container_width=True):
                                    tmpl_steps = tmpl.get("rules", {}).get("steps", [])
                                    queue = context.get("rule_queue") or []
                                    queue.extend(tmpl_steps)
                                    set_context(rule_queue=queue)
                                    set_flash(f"Đã nạp {len(tmpl_steps)} bước của '{tmpl['name']}' vào hàng đợi làm sạch.", "success")
                                    st.switch_page(get_page("suggestions").file)
                            with btn_c2:
                                if st.button("Mở để sửa", key=f"edit_tmpl_{tmpl['id']}", use_container_width=True, help="Nạp quy tắc vào trình soạn"):
                                    st.session_state["rule_builder_name"] = tmpl["name"]
                                    st.session_state["rule_builder_desc"] = tmpl.get("description") or ""
                                    st.session_state["rule_builder_steps"] = list(tmpl.get("rules", {}).get("steps", []))
                                    set_flash(f"Đã nạp '{tmpl['name']}' vào trình soạn quy tắc.", "info")
                                    st.rerun()
                            with btn_c3:
                                if confirm_button(
                                    "Xóa",
                                    key=f"del_tmpl_{tmpl['id']}",
                                    icon=":material/delete:",
                                    title=f"Xóa quy tắc '{tmpl['name']}'?",
                                    message="Quy tắc này sẽ bị xóa khỏi dự án. Thao tác này không thể hoàn tác.",
                                    confirm_label="Xóa vĩnh viễn",
                                    warning=True,
                                ):
                                    try:
                                        delete_rule_template(token, tmpl["id"])
                                        set_flash(f"Đã xóa quy tắc '{tmpl['name']}'.", "success")
                                        st.rerun()
                                    except APIError as exc:
                                        st.error(exc.detail)

    # --- PHẦN 3: TRÌNH SOẠN QUY TẮC NHIỀU BƯỚC (RULE BUILDER) ---
    st.markdown("---")
    st.markdown("### 🛠️ Trình soạn quy tắc nhiều bước")
    st.caption("Thiết lập chuỗi các bước biến đổi dữ liệu. Có thể kiểm tra tính hợp lệ và lưu lại vào dự án hiện tại.")

    name_col, desc_col = st.columns([4, 6])
    with name_col:
        st.session_state["rule_builder_name"] = st.text_input(
            "Tên quy tắc",
            value=st.session_state["rule_builder_name"],
            key="builder_input_name",
        )
    with desc_col:
        st.session_state["rule_builder_desc"] = st.text_input(
            "Mô tả (tùy chọn)",
            value=st.session_state["rule_builder_desc"],
            key="builder_input_desc",
        )

    editor_mode = st.radio("Chế độ soạn thảo", ["Biểu mẫu (Form)", "Mã JSON"], horizontal=True, key="builder_editor_mode")

    current_steps: list[dict[str, Any]] = st.session_state["rule_builder_steps"]

    if editor_mode == "Biểu mẫu (Form)":
        if not current_steps:
            st.info("Chưa có bước nào trong quy tắc. Bấm '+ Thêm bước' để bắt đầu.")
        else:
            for idx, step in enumerate(current_steps):
                with st.container(border=True):
                    sc1, sc2, sc3, sc4, sc5 = st.columns([3, 3, 3, 1, 1], vertical_alignment="center")
                    with sc1:
                        selected_op = st.selectbox(
                            f"Bước {idx + 1} - Phép biến đổi",
                            options=ALLOWED_OPS,
                            index=ALLOWED_OPS.index(step.get("op", ALLOWED_OPS[0])) if step.get("op") in ALLOWED_OPS else 0,
                            key=f"step_op_{idx}",
                        )
                        step["op"] = selected_op
                    with sc2:
                        # Dropdown cột nếu có dataset, hoặc text input
                        current_col = step.get("column", "")
                        if available_cols:
                            col_options = ["*text"] + available_cols
                            step["column"] = st.selectbox(
                                "Cột áp dụng",
                                options=col_options,
                                index=col_options.index(current_col) if current_col in col_options else 0,
                                key=f"step_col_select_{idx}",
                            )
                        else:
                            step["column"] = st.text_input(
                                "Tên cột",
                                value=current_col,
                                key=f"step_col_text_{idx}",
                            )
                    with sc3:
                        # Cấu hình tham số nhanh (dưới dạng JSON params)
                        params_str = json.dumps(step.get("params", {}), ensure_ascii=False)
                        new_params_str = st.text_input("Tham số (JSON)", value=params_str, key=f"step_params_{idx}")
                        try:
                            step["params"] = json.loads(new_params_str)
                        except Exception:
                            pass
                    with sc4:
                        up_disabled = (idx == 0)
                        down_disabled = (idx == len(current_steps) - 1)
                        m1, m2 = st.columns(2)
                        with m1:
                            if st.button("↑", key=f"step_up_{idx}", disabled=up_disabled, help="Di chuyển lên"):
                                current_steps[idx], current_steps[idx - 1] = current_steps[idx - 1], current_steps[idx]
                                st.rerun()
                        with m2:
                            if st.button("↓", key=f"step_down_{idx}", disabled=down_disabled, help="Di chuyển xuống"):
                                current_steps[idx], current_steps[idx + 1] = current_steps[idx + 1], current_steps[idx]
                                st.rerun()
                    with sc5:
                        if st.button("✕", key=f"step_del_{idx}", help="Xóa bước này", type="secondary"):
                            current_steps.pop(idx)
                            st.rerun()

        if st.button("+ Thêm bước", icon=":material/add:", key="builder_add_step_btn"):
            current_steps.append({"op": "trim_whitespace", "column": available_cols[0] if available_cols else "cot_moi", "params": {}})
            st.rerun()

    else:
        # Chế độ JSON
        json_raw = json.dumps(
            {
                "name": st.session_state["rule_builder_name"],
                "description": st.session_state["rule_builder_desc"],
                "steps": current_steps,
            },
            indent=2,
            ensure_ascii=False,
        )
        new_json_raw = st.text_area(
            "Cấu trúc JSON (theo rule_dsl.md)",
            value=json_raw,
            height=260,
            key="builder_json_textarea",
        )
        try:
            parsed = json.loads(new_json_raw)
            if isinstance(parsed, dict) and "steps" in parsed:
                st.session_state["rule_builder_steps"] = parsed["steps"]
                if "name" in parsed:
                    st.session_state["rule_builder_name"] = parsed["name"]
                if "description" in parsed:
                    st.session_state["rule_builder_desc"] = parsed["description"]
        except Exception as e:
            st.error(f"Cú pháp JSON chưa đúng: {e}")

    # Bảng điều khiển hành động: Kiểm tra hợp lệ, Xem trước, Lưu quy tắc, Xuất JSON
    st.markdown("")
    act_col1, act_col2, act_col3, act_col4 = st.columns([3, 3, 3, 3])
    
    with act_col1:
        if st.button("Kiểm tra hợp lệ", icon=":material/check:", use_container_width=True):
            rule_payload = {"steps": st.session_state["rule_builder_steps"]}
            is_valid, msgs = _validate_rule_set(rule_payload, available_cols)
            if is_valid:
                st.success(" Quy tắc hợp lệ theo chuẩn rule_dsl.md!", icon=":material/verified:")
                if msgs:
                    for m in msgs:
                        st.warning(m)
            else:
                for err in msgs:
                    st.error(err, icon=":material/error:")

    with act_col2:
        export_payload = json.dumps(
            {
                "name": st.session_state["rule_builder_name"],
                "description": st.session_state["rule_builder_desc"],
                "steps": st.session_state["rule_builder_steps"],
            },
            indent=2,
            ensure_ascii=False,
        )
        st.download_button(
            label="Xuất JSON",
            data=export_payload,
            file_name="ruleset.json",
            mime="application/json",
            icon=":material/download:",
            use_container_width=True,
        )

    with act_col3:
        if active_dataset and st.button("Xem trước trên dataset", icon=":material/preview:", use_container_width=True):
            version_id = active_dataset.get("current_version_id")
            if version_id and token:
                try:
                    res = preview_rules(token, version_id, st.session_state["rule_builder_steps"])
                    st.success(f"Xem trước thành công: {res.get('affected_row_count', 0)} dòng bị ảnh hưởng, {len(res.get('diffs', []))} ô thay đổi.")
                except APIError as exc:
                    st.error(f"Lỗi xem trước: {exc.detail}")
            else:
                st.warning("Dataset chưa có phiên bản khả dụng để xem trước.")

    with act_col4:
        if st.button("Lưu quy tắc", type="primary", icon=":material/save:", use_container_width=True):
            if not project_id:
                st.error("Vui lòng chọn Dự án để lưu quy tắc.")
            elif not st.session_state["rule_builder_name"].strip():
                st.error("Vui lòng nhập tên quy tắc.")
            else:
                rule_payload = {"steps": st.session_state["rule_builder_steps"]}
                is_valid, msgs = _validate_rule_set(rule_payload)
                if not is_valid:
                    st.error("Quy tắc chưa hợp lệ. Vui lòng kiểm tra lại các bước.")
                else:
                    try:
                        create_rule_template(
                            token,
                            project_id,
                            name=st.session_state["rule_builder_name"].strip(),
                            description=st.session_state["rule_builder_desc"].strip() or None,
                            rules=rule_payload,
                        )
                        set_flash("Đã lưu quy tắc mới thành công vào dự án! Bản cũ (nếu có) vẫn được giữ, xóa nếu không cần.", "success")
                        st.rerun()
                    except APIError as exc:
                        st.error(f"Không thể lưu quy tắc: {exc.detail}")

    st.caption("ℹ️ *Ghi chú: Nút 'Lưu' luôn tạo một bản ghi quy tắc mới trong dự án. Bản cũ vẫn được giữ nguyên, bạn có thể xóa nếu không cần thiết.*")


# Điểm vào chính của view
render_rule_library_view()

