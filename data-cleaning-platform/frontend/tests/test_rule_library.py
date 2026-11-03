"""Kiểm thử thư viện quy tắc, trình soạn và hợp đồng API."""

import re
from pathlib import Path

import pytest
import streamlit as st
from conftest import find_button

from components.rule_catalog import SUPPORTED_RULE_OPS
from views.rule_library import _parse_rule_document, _serialize_rule_document

CONTEXT = {"work_context": {"project_id": 1, "dataset_id": 1}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _open(run_view, **extra):
    return run_view("rule_library", role="user", state={**CONTEXT, **extra})


def test_system_rule_catalog_matches_documented_dsl():
    docs_path = Path(__file__).parents[2] / "docs" / "rule_dsl.md"
    documented_ops = set(
        re.findall(
            r"^\| `([a-z_]+)` \|",
            docs_path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    assert set(SUPPORTED_RULE_OPS) == documented_ops
    assert len(SUPPORTED_RULE_OPS) == 13


def test_create_rule_template_uses_backend_rule_set_contract(call_api):
    rule_set = {"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]}
    created, error, db = call_api(
        "user",
        "create_rule_template",
        1,
        "Chuẩn hóa email",
        rule_set=rule_set,
    )
    assert error is None
    assert created["rule_set"] == rule_set
    assert db["rules"][-1]["rule_set"] == rule_set


def test_library_renders_system_and_project_tabs(run_view):
    at = _open(run_view)
    assert not at.exception
    labels = [tab.label for tab in at.tabs]
    assert "Quy tắc hệ thống (13)" in labels
    assert "Quy tắc của dự án" in labels
    assert {code.value for code in at.code if code.language == "text"} == {
        f"op: {op}" for op in SUPPORTED_RULE_OPS
    }


def test_builder_validates_valid_missing_column_and_bad_json(run_view):
    at = _open(run_view)
    at.button(key="builder_add_step_btn").click().run()
    step_id = at.session_state["rule_builder_step_ids"][0]
    at.text_input(key=f"rule_step_{step_id}_column").set_value("email").run()
    at.button(key="validate_rule_builder").click().run()
    assert any("Quy tắc hợp lệ" in item.value for item in at.success)

    at.text_input(key=f"rule_step_{step_id}_column").set_value("column_not_found").run()
    at.button(key="validate_rule_builder").click().run()
    assert any("không tồn tại" in item.value for item in at.error)

    at.radio(key="builder_editor_mode").set_value("Mã JSON").run()
    at.text_area(key="builder_json_textarea").set_value("{broken").run()
    assert any("Cú pháp JSON chưa đúng" in item.value for item in at.error)


def test_switching_form_and_json_preserves_rule_data(run_view):
    at = _open(run_view)
    at.button(key="builder_add_step_btn").click().run()
    step_id = at.session_state["rule_builder_step_ids"][0]
    at.text_input(key=f"rule_step_{step_id}_column").set_value("email").run()

    at.radio(key="builder_editor_mode").set_value("Mã JSON").run()
    assert '"column": "email"' in at.text_area(key="builder_json_textarea").value
    json_document = (
        '{"name":"Email mới","description":"Mô tả","steps":'
        '[{"op":"trim_whitespace","column":"so_dien_thoai","params":{}}]}'
    )
    at.text_area(key="builder_json_textarea").set_value(json_document).run()
    at.radio(key="builder_editor_mode").set_value("Biểu mẫu (Form)").run()
    assert at.session_state["rule_builder_steps"][0]["column"] == "so_dien_thoai"
    assert at.session_state["rule_builder_name"] == "Email mới"


def test_builder_can_add_reorder_and_delete_steps(run_view):
    at = _open(run_view)
    at.button(key="builder_add_step_btn").click().run()
    first_step_id = at.session_state["rule_builder_step_ids"][0]
    at.button(key="builder_add_step_btn").click().run()
    second_step_id = at.session_state["rule_builder_step_ids"][1]

    at.button(key=f"rule_step_down_{first_step_id}").click().run()
    assert at.session_state["rule_builder_step_ids"] == [second_step_id, first_step_id]

    at.button(key=f"rule_step_delete_{first_step_id}").click().run()
    assert at.session_state["rule_builder_step_ids"] == [second_step_id]
    assert len(at.session_state["rule_builder_steps"]) == 1


def test_open_and_save_creates_a_new_rule_without_replacing_old(call_api, run_view):
    original_set = {"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]}
    original, error, db = call_api(
        "user", "create_rule_template", 1, "Bản gốc", rule_set=original_set
    )
    assert error is None

    at = _open(run_view, _mock_db=db)
    at.button(key=f"edit_tmpl_{original['id']}").click().run()
    assert at.session_state["rule_builder_name"] == "Bản gốc"
    at.button(key="save_rule_template").click().run()

    rules = at.session_state["_mock_db"]["rules"]
    assert len(rules) == 2
    assert rules[0]["id"] == original["id"]
    assert rules[0]["name"] == "Bản gốc"
    assert rules[1]["rule_set"] == original_set


def test_delete_rule_requires_confirmation(run_view, call_api):
    template, error, db = call_api(
        "user",
        "create_rule_template",
        1,
        "Quy tắc cần xóa",
        rule_set={"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]},
    )
    assert error is None

    at = _open(run_view, _mock_db=db)
    delete_key = f"del_tmpl_{template['id']}"
    at.button(key=delete_key).click().run()

    assert any("không thể hoàn tác" in item.value for item in at.warning)
    assert any(button.key == f"{delete_key}__ok" for button in at.button)
    assert any(rule["id"] == template["id"] for rule in at.session_state["_mock_db"]["rules"])

    at.session_state[f"{delete_key}__confirmed"] = True
    at.run()
    assert not any(rule["id"] == template["id"] for rule in at.session_state["_mock_db"]["rules"])


def test_exported_rule_json_can_be_imported_without_data_loss(run_view):
    rule_set = {"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]}
    at = _open(
        run_view,
        rule_builder_name="Chuẩn hóa email",
        rule_builder_desc="Rule dự án",
        rule_builder_steps=rule_set["steps"],
        rule_builder_step_ids=["step-1"],
        builder_input_name="Chuẩn hóa email",
        builder_input_desc="Rule dự án",
    )
    assert len(at.get("download_button")) == 1
    exported = _serialize_rule_document("Chuẩn hóa email", "Rule dự án", rule_set["steps"])
    imported, error = _parse_rule_document(exported)

    assert error is None
    assert imported == {
        "name": "Chuẩn hóa email",
        "description": "Rule dự án",
        **rule_set,
    }


def test_preview_action_loads_steps_into_cleaning_queue(run_view):
    at = _open(run_view)
    at.button(key="builder_add_step_btn").click().run()
    step_id = at.session_state["rule_builder_step_ids"][0]
    at.text_input(key=f"rule_step_{step_id}_column").set_value("email").run()
    find_button(at, "Xem trước trên dataset").click().run()

    queue = at.session_state["work_context"]["rule_queue"]
    assert queue[0]["source"] == "library"
    assert queue[0]["step"]["column"] == "email"
    assert at.session_state["work_context"]["rule_queue_version_id"] == 1
