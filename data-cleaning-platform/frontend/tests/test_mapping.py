"""Bước Mapping cột: logic thuần, gợi ý của mock (tầng 1) và trang."""

from pathlib import Path

import pytest
import streamlit as st
from conftest import find_button

import mock_mapping
from components.mapping_logic import (
    KEEP,
    build_rename_steps,
    duplicate_names,
    final_names,
    parse_target_schema,
)

FIXTURES = Path(__file__).parent / "fixtures"
SOURCE = FIXTURES / "khach_hang_tieu_de_khac.csv"
HEADERS = ["Họ và tên", "Email liên hệ", "Số ĐT", "Ngày sinh", "Tuổi", "Tỉnh/Thành phố", "Ghi chú"]
TARGETS = ["ho_ten", "email", "so_dien_thoai", "ngay_sinh", "tuoi", "tinh_thanh"]


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


# ---------------------------------------------------------------- logic thuần


def test_parse_target_schema_splits_trims_and_dedupes():
    names, problems = parse_target_schema(" ho_ten\nemail, so_dien_thoai ;\n\nemail \n")
    assert names == ["ho_ten", "email", "so_dien_thoai"] and problems == []


def test_parse_target_schema_rejects_empty_and_too_long():
    assert parse_target_schema("  \n ,")[1] == ["Vui lòng nhập ít nhất một cột chuẩn."]
    assert "tối đa 255" in parse_target_schema("x" * 256)[1][0]


def test_final_names_and_duplicates():
    sources, choices = ["a", "b", "c"], [KEEP, "a", "x"]
    assert final_names(sources, choices) == ["a", "a", "x"]
    assert duplicate_names(sources, choices) == ["a"]  # b đổi thành a trùng với cột a giữ nguyên
    assert duplicate_names(["a", "b"], ["x", "y"]) == []


def test_build_rename_steps_matches_rule_dsl():
    steps = build_rename_steps(["Họ và tên", "email", "Ghi chú"], ["ho_ten", "email", KEEP])
    assert steps == [
        {"op": "rename_column", "column": "Họ và tên", "params": {"new_name": "ho_ten"}}
    ]


# ---------------------------------------------------------------- mock tầng 1


def test_mock_suggestion_uses_synonyms_ignoring_accents_and_case():
    result = mock_mapping.suggest_mapping(HEADERS, TARGETS)
    assert result == {
        "Họ và tên": "ho_ten",
        "Email liên hệ": None,  # không có trong từ điển và không đủ giống
        "Số ĐT": "so_dien_thoai",
        "Ngày sinh": "ngay_sinh",
        "Tuổi": "tuoi",
        "Tỉnh/Thành phố": "tinh_thanh",
        "Ghi chú": None,
    }


def test_mock_suggestion_accepts_exact_target_and_fuzzy_typo():
    result = mock_mapping.suggest_mapping(["email", "EMAIL ", "emial"], ["email"])
    assert result == {"email": "email", "EMAIL ": "email", "emial": "email"}


# ---------------------------------------------------------------- API + trang


def _upload_demo(call_api):
    result, error, db = call_api(
        "user", "upload_dataset", 1, "khach_hang_tieu_de_khac.csv", SOURCE.read_bytes(), None
    )
    assert error is None
    return result["dataset"]["id"], db


def test_api_suggest_mapping_validation(call_api):
    dataset_id, db = _upload_demo(call_api)
    version_id = db["datasets"][-1]["current_version_id"]
    result, error, _ = call_api(
        "user", "suggest_mapping", version_id, TARGETS, state={"_mock_db": db}
    )
    assert error is None and result["Số ĐT"] == "so_dien_thoai"
    _, error, _ = call_api("user", "suggest_mapping", version_id, [], state={"_mock_db": db})
    assert error.status_code == 422
    assert dataset_id == db["datasets"][-1]["id"]


def _page(run_view, call_api, **extra):
    dataset_id, db = _upload_demo(call_api)
    state = {"_mock_db": db, "work_context": {"dataset_id": dataset_id}, **extra}
    return run_view("mapping", role="user", state=state)


TARGETS_TEXT = "\n".join(TARGETS)


def _suggest(at, text=TARGETS_TEXT):
    at.text_area(key="mapping_target_text").set_value(text).run()
    find_button(at, "Gợi ý mapping").click().run()
    return at


def _boxes(at):
    """Ô chọn cột đích, bỏ các ô chọn project/dataset trong header và thanh ngữ cảnh."""
    excluded = ("ctx_open", "header_")
    return [s for s in at.selectbox if not str(s.key).startswith(excluded)]


def test_page_renders_schema_form_without_suggestion(run_view, call_api):
    at = _page(run_view, call_api)
    assert not at.exception
    assert [t.label for t in at.text_area] == ["Danh sách cột chuẩn"]
    assert not _boxes(at)  # chưa gợi ý thì chưa có bảng mapping


def test_page_empty_schema_shows_problem(run_view, call_api):
    at = _suggest(_page(run_view, call_api), text="   ")
    assert any("ít nhất một cột chuẩn" in e.value for e in at.error)


def test_page_shows_suggestions_with_status_and_counts(run_view, call_api):
    at = _suggest(_page(run_view, call_api))
    assert not at.exception
    assert len(_boxes(at)) == len(HEADERS)
    defaults = [s.value for s in _boxes(at)]
    assert defaults == ["ho_ten", KEEP, "so_dien_thoai", "ngay_sinh", "tuoi", "tinh_thanh", KEEP]
    metrics = {m.label: m.value for m in at.metric}
    assert metrics == {"Cột trong file": "7", "Gợi ý khớp": "5/7", "Sẽ đổi tên": "5"}
    html = " ".join(m.value for m in at.markdown)
    assert html.count("Chưa khớp") == 2 and html.count("Gợi ý<") == 5


def test_page_manual_choice_and_confirm_builds_steps(run_view, call_api):
    at = _suggest(_page(run_view, call_api))
    _boxes(at)[1].set_value("email").run()  # chọn tay cho "Email liên hệ"
    assert {m.label: m.value for m in at.metric}["Sẽ đổi tên"] == "6"
    find_button(at, "Xác nhận mapping").click().run()
    context = at.session_state["work_context"]
    steps = context["pending_steps"]
    assert len(steps) == 6 and context["pending_version_id"] == context["version_id"]
    assert {
        "op": "rename_column",
        "column": "Email liên hệ",
        "params": {"new_name": "email"},
    } in steps
    assert all(s["op"] == "rename_column" for s in steps)


def test_page_duplicate_target_blocks_confirm(run_view, call_api):
    at = _suggest(_page(run_view, call_api))
    _boxes(at)[1].set_value("ho_ten").run()  # trùng với "Họ và tên" -> ho_ten
    assert any("hai cột cùng tên" in e.value for e in at.error)
    assert find_button(at, "Xác nhận mapping").disabled
    assert "pending_steps" not in at.session_state["work_context"]


def test_page_nothing_to_rename_disables_confirm(run_view, call_api):
    at = _suggest(_page(run_view, call_api), text="Ghi chú")  # chỉ chuẩn trùng tên cột đã có
    assert any("Không có cột nào cần đổi tên" in i.value for i in at.info)
    assert find_button(at, "Xác nhận mapping").disabled
    assert any(b.label == "Bỏ qua bước này" for b in at.button)


def test_page_example_button_fills_schema(run_view, call_api):
    at = _page(run_view, call_api)
    find_button(at, "Điền ví dụ").click().run()
    assert at.text_area(key="mapping_target_text").value.split("\n") == TARGETS


def test_page_without_dataset_shows_empty_state(run_view):
    at = run_view("mapping", role="user")
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)
