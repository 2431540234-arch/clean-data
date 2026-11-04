"""Thẻ "Quy trình làm sạch": trạng thái từng bước tính từ dataset đang chọn."""

import pytest
import streamlit as st

from components.workflow_status import DOING, DONE, TODO, workflow_status

KEYS = ["upload", "overview", "mapping", "suggestions", "history", "export"]


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _status(**kwargs):
    base = {"has_dataset": True, "profiled": False, "versions": [{}], "exported": False}
    return workflow_status(**{**base, **kwargs})


def test_no_dataset_everything_todo():
    assert workflow_status(has_dataset=False, profiled=True, versions=[{}, {}], exported=True) == {
        key: TODO for key in KEYS
    }


def test_fresh_upload_is_done_and_overview_in_progress():
    status = _status()
    assert status["upload"] == DONE
    assert status["overview"] == DOING
    assert [status[k] for k in KEYS[2:]] == [TODO] * 4


def test_profiled_moves_progress_to_next_step():
    status = _status(profiled=True)
    assert (status["overview"], status["mapping"]) == (DONE, DOING)


def test_cleaned_versions_finish_suggestions_and_history():
    versions = [{}, {"change_summary": "Áp dụng 2 bước: Xóa trùng lặp"}]
    status = _status(profiled=True, versions=versions)
    assert status["mapping"] == TODO  # chưa đổi tên cột: bước bị bỏ qua, không gắn Xong
    assert status["suggestions"] == status["history"] == DONE
    assert status["export"] == DOING


def test_rename_in_any_version_marks_mapping_done():
    versions = [{}, {"change_summary": "Áp dụng 1 bước: Đổi tên cột"}]
    assert _status(profiled=True, versions=versions)["mapping"] == DONE


def test_pending_mapping_is_in_progress():
    assert _status(profiled=True, mapping_pending=True)["mapping"] == DOING


def test_exported_everything_done_when_all_steps_taken():
    versions = [{}, {"change_summary": "Đổi tên cột"}]
    status = _status(profiled=True, versions=versions, exported=True)
    assert set(status.values()) == {DONE}


def _badges(at):
    return [m.value for m in at.markdown if any(s in m.value for s in (DONE, DOING, TODO))]


def test_home_without_dataset_shows_all_todo(run_view):
    at = run_view("home", role="user")
    assert not at.exception
    flow = [v for v in _badges(at) if "<" in v]
    assert len(flow) == 6
    assert all(TODO in v for v in flow)


def test_home_with_dataset_reflects_real_state(run_view):
    at = run_view("home", role="user", state={"work_context": {"dataset_id": 1}})
    assert not at.exception
    flow = [v for v in _badges(at) if "<" in v]
    assert len(flow) == 6
    assert DONE in flow[0]  # đã tải lên
    assert not all(TODO in v for v in flow)
