"""Quản lý quy tắc hệ thống và quy tắc của dự án."""

import hashlib
import json
from typing import Any

import streamlit as st

from api_client import (
    APIError,
    create_rule_template,
    delete_rule_template,
    list_rule_templates,
)
from components.dataset_context import dataset_context_bar, load_profile
from components.navigation import get_page
from components.rule_catalog import (
    SUPPORTED_RULE_OPS,
    SYSTEM_RULE_CATEGORIES,
    SYSTEM_RULES,
    get_system_rule,
)
from components.rule_queue import add_queue_steps
from components.rule_validation import validate_rule_set
from components.ui import (
    confirm_button,
    empty_state,
    error_state,
    page_shell,
    safe_call,
)
from state import get_context, get_token, set_context, set_flash

_FORM_MODE = "Biểu mẫu (Form)"
_JSON_MODE = "Mã JSON"


def _serialize_rule_document(name: str, description: str, steps: list[dict[str, Any]]) -> str:
    return json.dumps(
        {"name": name, "description": description, "steps": steps},
        indent=2,
        ensure_ascii=False,
    )


def _parse_rule_document(raw: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, f"Cú pháp JSON chưa đúng: {exc.msg}."
    if not isinstance(document, dict):
        return None, "Nội dung JSON phải là một đối tượng."
    if not isinstance(document.get("steps"), list):
        return None, "RuleSet phải có trường 'steps' dạng danh sách."
    if not isinstance(document.get("name", ""), str):
        return None, "Tên quy tắc phải là chuỗi."
    if not isinstance(document.get("description", ""), str):
        return None, "Mô tả phải là chuỗi."
    if any(not isinstance(step, dict) for step in document["steps"]):
        return None, "Mỗi bước trong 'steps' phải là một đối tượng."
    return document, None


def _rule_set(template: dict[str, Any]) -> dict[str, Any]:
    """Đọc schema thật và giữ tương thích với dữ liệu mock/legacy cũ."""
    rule_set = template.get("rule_set") or template.get("rules") or {}
    return rule_set if isinstance(rule_set, dict) else {}


def _next_step_id() -> str:
    identifier = st.session_state.get("_rule_builder_next_step_id", 0)
    st.session_state["_rule_builder_next_step_id"] = identifier + 1
    return str(identifier)


def _set_builder(name: str, description: str, steps: list[dict[str, Any]]) -> None:
    copied_steps = [dict(step) for step in steps]
    st.session_state["rule_builder_name"] = name
    st.session_state["rule_builder_desc"] = description
    st.session_state["rule_builder_steps"] = copied_steps
    st.session_state["rule_builder_step_ids"] = [_next_step_id() for _ in copied_steps]
    st.session_state["builder_input_name"] = name
    st.session_state["builder_input_desc"] = description
    st.session_state["builder_editor_mode"] = _FORM_MODE
    st.session_state["_rule_builder_last_mode"] = _FORM_MODE
    st.session_state.pop("builder_json_textarea", None)
    st.session_state["rule_validation_requested"] = False


def _init_builder_state() -> None:
    st.session_state.setdefault("rule_builder_name", "Quy tắc làm sạch mới")
    st.session_state.setdefault("rule_builder_desc", "")
    st.session_state.setdefault("rule_builder_steps", [])
    if "rule_builder_step_ids" not in st.session_state:
        st.session_state["rule_builder_step_ids"] = [
            _next_step_id() for _ in st.session_state["rule_builder_steps"]
        ]
    if len(st.session_state["rule_builder_step_ids"]) != len(
        st.session_state["rule_builder_steps"]
    ):
        st.session_state["rule_builder_step_ids"] = [
            _next_step_id() for _ in st.session_state["rule_builder_steps"]
        ]
    st.session_state.setdefault("builder_input_name", st.session_state["rule_builder_name"])
    st.session_state.setdefault("builder_input_desc", st.session_state["rule_builder_desc"])
    st.session_state.setdefault("builder_editor_mode", _FORM_MODE)
    st.session_state.setdefault("_rule_builder_last_mode", _FORM_MODE)
    st.session_state.setdefault("rule_validation_requested", False)


def _import_document(uploaded_file: Any) -> None:
    content = uploaded_file.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    if digest == st.session_state.get("_last_rule_import_digest"):
        return
    try:
        raw = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        st.error("File JSON phải được mã hóa UTF-8.")
        return
    document, error = _parse_rule_document(raw)
    if error:
        st.error(error)
        return
    _set_builder(
        document.get("name", "Quy tắc nhập từ JSON"),
        document.get("description", ""),
        document["steps"],
    )
    st.session_state["_last_rule_import_digest"] = digest
    set_flash("Đã nạp quy tắc JSON vào trình soạn.", "success")
    st.rerun()


def _enqueue_and_open_cleaning(
    steps: list[dict[str, Any]], source: str, version_id: int, name: str
) -> None:
    queue = add_queue_steps(get_context().get("rule_queue"), steps, source=source)
    set_context(rule_queue=queue, rule_queue_version_id=version_id)
    set_flash(f"Đã nạp {len(steps)} bước của '{name}' vào hàng đợi.", "success")
    st.switch_page(get_page("suggestions").file)


def _render_system_rules(available_columns: list[str], version_id: int | None) -> None:
    st.caption(
        f"{len(SYSTEM_RULES)} quy tắc hệ thống theo DSL, chia thành "
        f"{len(SYSTEM_RULE_CATEGORIES)} nhóm."
    )
    selected_column = None
    if available_columns:
        selected_column = st.selectbox(
            "Cột áp dụng cho quy tắc cần cột",
            available_columns,
            key="library_system_column",
        )
    elif version_id:
        st.warning("Không lấy được danh sách cột của dataset.")
    else:
        st.info("Mở dataset để đưa quy tắc hệ thống vào hàng đợi làm sạch.")

    for category in SYSTEM_RULE_CATEGORIES:
        st.markdown(f"#### {category}")
        rules = [rule for rule in SYSTEM_RULES if rule.category == category]
        columns = st.columns(2)
        for index, rule in enumerate(rules):
            with columns[index % 2], st.container(border=True):
                st.markdown(f"**:material/{rule.icon}: {rule.name}**")
                st.caption(rule.description)
                st.code(f"op: {rule.op}", language="text")
                step = {"op": rule.op, "params": dict(rule.default_params)}
                if rule.requires_column and selected_column:
                    step["column"] = selected_column
                if st.button(
                    "Dùng",
                    key=f"use_sys_{rule.id}",
                    type="secondary",
                    use_container_width=True,
                    disabled=not version_id or (rule.requires_column and selected_column is None),
                ):
                    _enqueue_and_open_cleaning([step], "system", version_id, rule.name)


def _render_project_rules(project_id: int | None, token: str | None) -> None:
    if not project_id:
        st.info("Chọn dự án ở thanh menu trên cùng để xem quy tắc của dự án.")
        return
    if not token:
        st.error("Phiên đăng nhập hết hạn. Vui lòng đăng nhập lại.")
        return

    templates, error = safe_call("Đang tải quy tắc dự án…", list_rule_templates, token, project_id)
    if error is not None:
        error_state(error, key="load_rule_templates")
        return
    if not templates:
        empty_state(
            "library_books",
            "Chưa có quy tắc nào trong dự án này",
            "Tạo quy tắc ở trình soạn bên dưới rồi lưu vào dự án.",
        )
        return

    st.caption(f"{len(templates)} quy tắc trong dự án hiện tại.")
    for template in templates:
        rule_set = _rule_set(template)
        steps = rule_set.get("steps", [])
        with st.container(border=True):
            details, use_col, edit_col, delete_col = st.columns([6, 1, 2, 1])
            with details:
                st.markdown(f"**{template['name']}**")
                if template.get("description"):
                    st.caption(template["description"])
                st.caption(
                    f"{len(steps)} bước · Tạo ngày " f"{str(template.get('created_at', ''))[:10]}"
                )
            with use_col:
                if st.button(
                    "Dùng",
                    key=f"apply_tmpl_{template['id']}",
                    type="primary",
                    use_container_width=True,
                    disabled=not get_context().get("version_id"),
                ):
                    _enqueue_and_open_cleaning(
                        steps,
                        "project",
                        get_context()["version_id"],
                        template["name"],
                    )
            with edit_col:
                if st.button(
                    "Mở để sửa",
                    key=f"edit_tmpl_{template['id']}",
                    use_container_width=True,
                ):
                    _set_builder(
                        template["name"],
                        template.get("description") or "",
                        steps,
                    )
                    set_flash(
                        f"Đã nạp '{template['name']}' vào trình soạn. "
                        "Lưu sẽ tạo một quy tắc mới.",
                        "info",
                    )
                    st.rerun()
            with delete_col:
                if confirm_button(
                    "Xóa",
                    key=f"del_tmpl_{template['id']}",
                    icon=":material/delete:",
                    title=f"Xóa quy tắc '{template['name']}'?",
                    message="Quy tắc này sẽ bị xóa khỏi dự án. Thao tác này không thể hoàn tác.",
                    confirm_label="Xóa vĩnh viễn",
                    warning=True,
                ):
                    try:
                        delete_rule_template(token, template["id"])
                    except APIError as exc:
                        error_state(exc, key=f"delete_rule_{template['id']}")
                    else:
                        set_flash(f"Đã xóa quy tắc '{template['name']}'.", "success")
                        st.rerun()


def _render_form_editor(
    steps: list[dict[str, Any]], step_ids: list[str], available_columns: list[str]
) -> list[str]:
    errors = []
    if not steps:
        st.info("Chưa có bước. Bấm “Thêm bước” để bắt đầu soạn quy tắc.")
    for index, (step, step_id) in enumerate(zip(steps, step_ids, strict=True)):
        with st.container(border=True):
            op_col, column_col, params_col, up_col, down_col, delete_col = st.columns(
                [2, 2, 4, 1, 1, 1]
            )
            with op_col:
                op_key = f"rule_step_{step_id}_op"
                st.session_state.setdefault(op_key, step.get("op", SUPPORTED_RULE_OPS[0]))
                step["op"] = st.selectbox(
                    "Phép biến đổi",
                    SUPPORTED_RULE_OPS,
                    format_func=lambda op: get_system_rule(op).name,
                    key=op_key,
                )
            rule = get_system_rule(step["op"])
            if rule and rule.requires_column:
                with column_col:
                    column_key = f"rule_step_{step_id}_column"
                    st.session_state.setdefault(column_key, step.get("column", ""))
                    step["column"] = st.text_input("Cột áp dụng", key=column_key)
            else:
                step.pop("column", None)
                with column_col:
                    st.caption("Không cần cột" if rule else "")
            with params_col:
                params_key = f"rule_step_{step_id}_params"
                st.session_state.setdefault(
                    params_key,
                    json.dumps(step.get("params", {}), ensure_ascii=False),
                )
                params_text = st.text_input("Tham số (JSON)", key=params_key)
                try:
                    params = json.loads(params_text)
                    if not isinstance(params, dict):
                        raise ValueError("Tham số phải là một đối tượng JSON.")
                    step["params"] = params
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(f"Bước {index + 1}: tham số JSON không hợp lệ ({exc}).")
            with up_col:
                if st.button(
                    "↑",
                    key=f"rule_step_up_{step_id}",
                    disabled=index == 0,
                    help="Di chuyển lên",
                ):
                    steps[index - 1], steps[index] = steps[index], steps[index - 1]
                    step_ids[index - 1], step_ids[index] = step_ids[index], step_ids[index - 1]
                    st.rerun()
            with down_col:
                if st.button(
                    "↓",
                    key=f"rule_step_down_{step_id}",
                    disabled=index == len(steps) - 1,
                    help="Di chuyển xuống",
                ):
                    steps[index + 1], steps[index] = steps[index], steps[index + 1]
                    step_ids[index + 1], step_ids[index] = step_ids[index], step_ids[index + 1]
                    st.rerun()
            with delete_col:
                if st.button("✕", key=f"rule_step_delete_{step_id}", help="Xóa bước"):
                    steps.pop(index)
                    step_ids.pop(index)
                    st.rerun()

    if st.button("+ Thêm bước", key="builder_add_step_btn"):
        step = {"op": "trim_whitespace", "params": {}}
        if available_columns:
            step["column"] = available_columns[0]
        steps.append(step)
        step_ids.append(_next_step_id())
        st.rerun()
    return errors


def _render_json_editor(name: str, description: str, steps: list[dict[str, Any]]) -> str | None:
    if st.session_state["_rule_builder_last_mode"] != _JSON_MODE:
        st.session_state["builder_json_textarea"] = _serialize_rule_document(
            name, description, steps
        )
    st.session_state["_rule_builder_last_mode"] = _JSON_MODE
    raw = st.text_area(
        "Cấu trúc JSON theo rule_dsl.md",
        height=260,
        key="builder_json_textarea",
    )
    document, error = _parse_rule_document(raw)
    if error:
        st.error(error)
        return error

    if document is not None:
        new_steps = document["steps"]
        if new_steps != st.session_state["rule_builder_steps"]:
            st.session_state["rule_builder_steps"] = [dict(step) for step in new_steps]
            st.session_state["rule_builder_step_ids"] = [_next_step_id() for _ in new_steps]
        st.session_state["rule_builder_name"] = document.get("name", "")
        st.session_state["rule_builder_desc"] = document.get("description", "")
        st.session_state["_sync_rule_builder_inputs"] = True
    return None


def _render_builder(
    project_id: int | None,
    token: str | None,
    version_id: int | None,
    available_columns: list[str],
) -> None:
    st.markdown("---")
    st.markdown("### Trình soạn quy tắc nhiều bước")

    if st.session_state.pop("_sync_rule_builder_inputs", False):
        st.session_state["builder_input_name"] = st.session_state["rule_builder_name"]
        st.session_state["builder_input_desc"] = st.session_state["rule_builder_desc"]

    name_col, description_col = st.columns([4, 6])
    with name_col:
        st.text_input("Tên quy tắc", key="builder_input_name")
    with description_col:
        st.text_input("Mô tả (tùy chọn)", key="builder_input_desc")
    st.session_state["rule_builder_name"] = st.session_state["builder_input_name"]
    st.session_state["rule_builder_desc"] = st.session_state["builder_input_desc"]

    mode = st.radio(
        "Chế độ soạn thảo",
        [_FORM_MODE, _JSON_MODE],
        horizontal=True,
        key="builder_editor_mode",
    )
    steps: list[dict[str, Any]] = st.session_state["rule_builder_steps"]
    step_ids: list[str] = st.session_state["rule_builder_step_ids"]
    json_error = None
    form_errors: list[str] = []
    if mode == _FORM_MODE:
        if st.session_state["_rule_builder_last_mode"] == _JSON_MODE:
            st.session_state["_rule_builder_last_mode"] = _FORM_MODE
        form_errors = _render_form_editor(steps, step_ids, available_columns)
    else:
        json_error = _render_json_editor(
            st.session_state["rule_builder_name"],
            st.session_state["rule_builder_desc"],
            steps,
        )

    current_rule_set = {"steps": st.session_state["rule_builder_steps"]}
    is_valid, validation_errors = validate_rule_set(
        current_rule_set, available_columns if version_id else None
    )
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("Kiểm tra hợp lệ", key="validate_rule_builder"):
            st.session_state["rule_validation_requested"] = True
    if st.session_state["rule_validation_requested"]:
        if json_error or form_errors:
            for error in form_errors:
                st.error(error)
        elif is_valid:
            st.success("Quy tắc hợp lệ theo rule_dsl.md.")
        else:
            for error in validation_errors:
                st.error(error)

    with action_col2:
        st.download_button(
            "Xuất JSON",
            data=_serialize_rule_document(
                st.session_state["rule_builder_name"],
                st.session_state["rule_builder_desc"],
                st.session_state["rule_builder_steps"],
            ),
            file_name="ruleset.json",
            mime="application/json",
            key="export_rule_set",
        )
    with action_col3:
        if st.button(
            "Xem trước trên dataset",
            key="preview_rule_set",
            disabled=not version_id or not is_valid or json_error is not None or bool(form_errors),
        ):
            _enqueue_and_open_cleaning(
                st.session_state["rule_builder_steps"],
                "library",
                version_id,
                st.session_state["rule_builder_name"],
            )

    if st.button(
        "Lưu quy tắc",
        type="primary",
        key="save_rule_template",
        disabled=(
            not project_id
            or not token
            or not st.session_state["rule_builder_name"].strip()
            or not is_valid
            or json_error is not None
            or bool(form_errors)
        ),
    ):
        try:
            create_rule_template(
                token,
                project_id,
                name=st.session_state["rule_builder_name"].strip(),
                description=st.session_state["rule_builder_desc"].strip() or None,
                rule_set=current_rule_set,
            )
        except APIError as exc:
            error_state(exc, key="save_rule_template_error")
        else:
            set_flash(
                "Đã lưu quy tắc mới. Bản cũ vẫn được giữ nguyên.",
                "success",
            )
            st.rerun()
    st.caption("Mỗi lần lưu luôn tạo quy tắc mới; không ghi đè bản cũ.")


def render_rule_library_view() -> None:
    page_shell(
        "Thư viện quy tắc",
        "Dùng quy tắc hệ thống hoặc soạn bộ quy tắc nhiều bước cho dự án.",
        page_key="rule_library",
    )
    _init_builder_state()
    context = get_context()
    token = get_token()
    project_id = context.get("project_id")

    active = dataset_context_bar() if context.get("dataset_id") else None
    version_id = active.version["id"] if active else None
    available_columns = []
    if active:
        profile, profile_error = load_profile(version_id)
        if profile_error is not None:
            error_state(profile_error, key="rule_library_profile")
        else:
            available_columns = [column["column_name"] for column in profile.get("columns", [])]

    with st.popover("Nhập JSON", icon=":material/upload_file:"):
        st.caption("Nhập RuleSet theo chuẩn docs/rule_dsl.md.")
        uploaded_json = st.file_uploader("Chọn file JSON", type=["json"], key="import_ruleset_file")
        if uploaded_json is not None:
            _import_document(uploaded_json)

    tab_system, tab_project = st.tabs(
        [f"Quy tắc hệ thống ({len(SYSTEM_RULES)})", "Quy tắc của dự án"]
    )
    with tab_system:
        _render_system_rules(available_columns, version_id)
    with tab_project:
        _render_project_rules(project_id, token)

    _render_builder(project_id, token, version_id, available_columns)


render_rule_library_view()
