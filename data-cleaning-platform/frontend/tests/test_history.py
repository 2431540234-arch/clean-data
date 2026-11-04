"""Bước Lịch sử phiên bản: undo/redo/restore của mock và trang timeline."""

import pytest
import streamlit as st
from conftest import find_button

import api_client
from components.version_timeline import can_redo, can_undo

CONTEXT = {"work_context": {"dataset_id": 1}}
TRIM = {"op": "trim_whitespace", "column": "email", "params": {}}
DEDUP = {"op": "drop_duplicates", "column": None, "params": {}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _with_versions(call_api, *step_groups):
    """DB mock đã áp dụng lần lượt các nhóm bước (tạo phiên bản 2, 3, ...)."""
    db = None
    for steps in step_groups:
        state = {"_mock_db": db} if db else None
        _, error, db = call_api("user", "apply_rules", 1, steps, state=state)
        assert error is None
    return db


def _current(db):
    return next(d for d in db["datasets"] if d["id"] == 1)["current_version_id"]


# ---------------------------------------------------------------- logic can_undo/can_redo


def test_can_undo_and_redo_follow_parent_links():
    versions = [
        {"id": 1, "parent_version_id": None},
        {"id": 2, "parent_version_id": 1},
        {"id": 3, "parent_version_id": 2},
    ]
    assert not can_undo(versions, 1) and can_redo(versions, 1)
    assert can_undo(versions, 2) and can_redo(versions, 2)
    assert can_undo(versions, 3) and not can_redo(versions, 3)


# ---------------------------------------------------------------- API (mock)


def test_api_undo_redo_cycle(call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    assert _current(db) == 3

    undone, error, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    assert error is None and undone["version_number"] == 2 and _current(db) == 2
    undone, _, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    assert undone["version_number"] == 1
    _, error, _ = call_api("user", "undo_version", 1, state={"_mock_db": db})
    assert error.status_code == 422 and "Không còn phiên bản trước" in error.detail

    redone, error, db = call_api("user", "redo_version", 1, state={"_mock_db": db})
    assert error is None and redone["version_number"] == 2
    redone, _, db = call_api("user", "redo_version", 1, state={"_mock_db": db})
    assert redone["version_number"] == 3
    _, error, _ = call_api("user", "redo_version", 1, state={"_mock_db": db})
    assert error.status_code == 422 and "Không có phiên bản nào để làm lại" in error.detail


def test_api_undo_then_apply_creates_a_branch_and_redo_picks_latest(call_api):
    db = _with_versions(call_api, [DEDUP])
    _, _, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    _, error, db = call_api("user", "apply_rules", 1, [TRIM], state={"_mock_db": db})
    assert error is None
    versions, _, db = call_api("user", "list_dataset_versions", 1, state={"_mock_db": db})
    branch = next(v for v in versions if v["version_number"] == 3)
    assert branch["parent_version_id"] == 1  # nhánh mới từ phiên bản gốc
    _, _, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    redone, _, _ = call_api("user", "redo_version", 1, state={"_mock_db": db})
    assert redone["version_number"] == 3  # chọn phiên bản con mới nhất


def test_api_restore_and_errors(call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    restored, error, db = call_api("user", "restore_version", 1, 1, state={"_mock_db": db})
    assert error is None and restored["version_number"] == 1 and _current(db) == 1
    assert len(db["versions"]) == 3  # không xóa phiên bản nào
    _, error, _ = call_api("user", "restore_version", 1, 999, state={"_mock_db": db})
    assert error.status_code == 404
    _, error, _ = call_api("admin", "restore_version", 1, 1, state={"_mock_db": db})
    assert error is None  # admin được phép


# ---------------------------------------------------------------- trang


def test_page_with_only_original_version_shows_empty_state(run_view):
    at = run_view("history", role="user", state=CONTEXT)
    assert not at.exception
    assert any("Chưa có thay đổi nào" in m.value for m in at.markdown)
    assert find_button(at, "Hoàn tác").disabled and find_button(at, "Làm lại").disabled
    assert not [b for b in at.button if b.key and b.key.startswith("restore_")]  # chỉ có bản gốc
    assert any(b.label == "Đến Gợi ý làm sạch" for b in at.button)


def test_page_lists_versions_newest_first_with_current_marker(run_view, call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    at = run_view("history", role="user", state={**CONTEXT, "_mock_db": db})
    text = " ".join(m.value for m in at.markdown)
    assert text.index("Phiên bản 3") < text.index("Phiên bản 2") < text.index("Phiên bản 1")
    assert text.count("Hiện tại") == 1 and "Bản gốc" in text
    captions = " ".join(c.value for c in at.caption)
    assert "từ phiên bản 2" in captions and "−1 dòng" in captions
    undo = find_button(at, "Hoàn tác")
    redo = find_button(at, "Làm lại")
    assert not undo.disabled and redo.disabled
    assert [b.key for b in at.button if b.key and b.key.startswith("restore_")] == [
        "restore_2",
        "restore_1",
    ]


def test_page_detail_panel_defaults_to_current_and_view_button_switches(run_view, call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    at = run_view("history", role="user", state={**CONTEXT, "_mock_db": db})
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Chi tiết phiên bản 3" in text
    metrics = {m.label: m for m in at.metric}
    assert set(metrics) == {"Số dòng", "Số cột", "Điểm chất lượng"}
    assert metrics["Số dòng"].value == "29" and not metrics["Số dòng"].delta  # v3 không đổi dòng
    assert any(b.label == "Đang xem" and b.disabled for b in at.button)
    assert find_button(at, "Hoàn tác (về v2)")

    at.button(key="view_2").click().run()
    metrics = {m.label: m for m in at.metric}
    assert metrics["Số dòng"].delta == "-1 so v1"
    assert not metrics["Số cột"].delta

    at.button(key="view_1").click().run()
    assert not at.exception
    text = " ".join(m.value for m in at.markdown)
    assert "Chi tiết phiên bản 1" in text
    assert any("Bản gốc khi tải lên" in c.value for c in at.caption)
    assert {m.label: m.value for m in at.metric}["Số dòng"] == "30"
    assert _current(at.session_state["_mock_db"]) == 3  # chỉ xem, không đổi phiên bản hiện tại


def test_page_next_button_leads_to_export(run_view, call_api, monkeypatch):
    switched = []
    monkeypatch.setattr(st, "switch_page", lambda page: switched.append(page))
    at = run_view("history", role="user", state=CONTEXT)
    find_button(at, "Tiếp tục: Xuất dữ liệu").click().run()
    assert switched == ["views/export.py"]


def test_page_undo_and_redo_buttons(run_view, call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    at = run_view("history", role="user", state={**CONTEXT, "_mock_db": db})
    find_button(at, "Hoàn tác").click().run()
    assert not at.exception and _current(at.session_state["_mock_db"]) == 2
    assert not find_button(at, "Làm lại").disabled
    find_button(at, "Làm lại").click().run()
    assert _current(at.session_state["_mock_db"]) == 3


def test_page_undo_disabled_on_original_and_redo_available(run_view, call_api):
    db = _with_versions(call_api, [DEDUP])
    _, _, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    at = run_view("history", role="user", state={**CONTEXT, "_mock_db": db})
    assert find_button(at, "Hoàn tác").disabled and not find_button(at, "Làm lại").disabled


def test_page_restore_after_confirmation_resets_stale_state(run_view, call_api):
    db = _with_versions(call_api, [DEDUP], [TRIM])
    state = {**CONTEXT, "_mock_db": db, "restore_1__confirmed": True}
    state["work_context"] = {
        "dataset_id": 1,
        "preview": {"signature": "x"},
        "last_applied": {"x": 1},
    }
    at = run_view("history", role="user", state=state)
    assert not at.exception
    assert _current(at.session_state["_mock_db"]) == 1
    context = at.session_state["work_context"]
    assert context["preview"] is None and context["last_applied"] is None


def test_page_action_failure_is_shown_inline(run_view, call_api, monkeypatch):
    db = _with_versions(call_api, [DEDUP])

    def refuse(token, dataset_id):
        raise api_client.APIError(422, "Không còn phiên bản trước để hoàn tác.")

    monkeypatch.setattr(api_client, "undo_version", refuse)
    at = run_view("history", role="user", state={**CONTEXT, "_mock_db": db})
    find_button(at, "Hoàn tác").click().run()
    assert any("Không còn phiên bản trước" in e.value for e in at.error)


def test_page_load_error_and_no_dataset(run_view, monkeypatch):
    def boom(token, dataset_id):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "list_dataset_versions", boom)
    at = run_view("history", role="user", state=CONTEXT)
    assert not at.exception and any(b.label == "Thử lại" for b in at.button)
    assert any("chưa sẵn sàng" in e.value for e in at.error)
    at = run_view("history", role="user")
    assert any("Chưa chọn dataset" in m.value for m in at.markdown)
