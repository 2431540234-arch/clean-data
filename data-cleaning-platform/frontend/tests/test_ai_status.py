"""Trạng thái AI (header X-AI-Status): api_client đọc đúng và trang Làm sạch báo nhẹ nhàng."""

import pytest
import streamlit as st
from conftest import find_button

import api_client
import mock_api

CONTEXT = {"work_context": {"dataset_id": 1, "version_id": 1, "project_id": 1}}
DISABLED_NOTE = "Gợi ý đang dùng bộ quy tắc (AI chưa bật)."
FALLBACK_NOTE = "AI tạm thời không phản hồi, đã dùng bộ quy tắc."


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _captions(at):
    return [c.value for c in at.caption]


def _generate_in_ui(run_view, monkeypatch, mode):
    monkeypatch.setattr(mock_api, "AI_MODE", mode)
    at = run_view("suggestions", role="user", state=CONTEXT)
    find_button(at, "Sinh gợi ý").click().run()
    return at


@pytest.mark.parametrize("mode", ["used", "disabled", "fallback"])
def test_api_client_reads_status_header_for_generate(monkeypatch, call_api, mode):
    monkeypatch.setattr(mock_api, "AI_MODE", mode)
    headers: dict[str, str] = {}
    _, error, _ = call_api("user", "generate_suggestions", 1, headers)
    assert error is None
    assert api_client.ai_status_of(headers) == mode


def test_api_client_status_is_optional_and_validated():
    assert api_client.ai_status_of({}) is None
    assert api_client.ai_status_of({"x-ai-status": "la"}) is None
    assert api_client.ai_status_of({"x-ai-status": "used"}) == "used"


def test_old_call_without_status_out_still_works(call_api):
    suggestions, error, _ = call_api("user", "generate_suggestions", 1)
    assert error is None and suggestions


def test_ui_disabled_shows_rule_note(run_view, monkeypatch):
    at = _generate_in_ui(run_view, monkeypatch, "disabled")
    assert not at.exception
    assert DISABLED_NOTE in _captions(at)
    assert FALLBACK_NOTE not in _captions(at)


def test_ui_fallback_shows_temporary_note(run_view, monkeypatch):
    at = _generate_in_ui(run_view, monkeypatch, "fallback")
    assert FALLBACK_NOTE in _captions(at)
    assert DISABLED_NOTE not in _captions(at)


def test_ui_used_shows_no_note(run_view, monkeypatch):
    at = _generate_in_ui(run_view, monkeypatch, "used")
    assert not at.exception
    assert DISABLED_NOTE not in _captions(at) and FALLBACK_NOTE not in _captions(at)


def test_ui_reopening_page_still_shows_disabled_note(run_view, monkeypatch):
    """Danh sách đã lưu từ trước: trạng thái "disabled" suy ra từ phản hồi danh sách."""
    monkeypatch.setattr(mock_api, "AI_MODE", "disabled")
    assert api_client.generate_suggestions("mock-token-2", 1)  # đã có gợi ý lưu sẵn
    at = run_view("suggestions", role="user", state={**CONTEXT, "_mock_db": mock_api.db()})
    assert DISABLED_NOTE in _captions(at)


def test_mapping_status_only_when_something_was_unmatched(monkeypatch):
    monkeypatch.setattr(mock_api, "AI_MODE", "fallback")
    assert mock_api.ai_status("POST", "/mapping/1/suggest", {"a": None}) == "fallback"
    assert mock_api.ai_status("POST", "/mapping/1/suggest", {"a": "b"}) is None
