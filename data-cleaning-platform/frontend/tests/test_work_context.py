"""Ngữ cảnh làm việc sau khi tạo dự án / tải file (hàm thuần, không cần st.dialog)."""

import pytest
import streamlit as st

from components.work_context import project_context, uploaded_dataset_context

CSV = b"ho_ten,email\nAn,an@example.com\n"


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def test_project_context_selects_project_and_clears_everything_scoped_to_the_old_one():
    values = project_context({"id": 7, "name": "Dự án B"})
    assert values["project_id"] == 7 and values["project_name"] == "Dự án B"
    for key in ("dataset_id", "dataset_name", "version_id", "upload_result", "preview", "mapping"):
        assert values[key] is None
    assert values["rule_queue"] == []
    assert values["pending_steps"] is None and values["pending_version_id"] is None


def test_project_context_does_not_share_the_rule_queue_between_calls():
    first = project_context({"id": 1, "name": "A"})
    first["rule_queue"].append({"op": "drop_duplicates"})
    assert project_context({"id": 1, "name": "A"})["rule_queue"] == []


def test_uploaded_dataset_context_belongs_to_the_given_project():
    result = {
        "dataset": {"id": 5, "original_filename": "f.csv", "current_version_id": None},
        "first_version": {"id": 9},
    }
    values = uploaded_dataset_context(result, {"id": 7, "name": "Dự án B"})
    assert values["project_id"] == 7 and values["dataset_id"] == 5
    assert values["version_id"] == 9 and values["upload_result"] is result
    assert "project_id" not in uploaded_dataset_context(result, None)


def test_project_a_then_create_b_then_upload_goes_into_b(run_view, call_api):
    """Đang ở dự án A -> tạo dự án B -> tải file: file vào B và header cũng hiện B."""
    project_a = {"id": 1, "name": "Khách hàng 2026"}
    context = dict(project_context(project_a))

    project_b, error, db = call_api("user", "create_project", "Dự án B")
    assert error is None and project_b["id"] != project_a["id"]
    context.update(project_context(project_b))  # đúng thao tác của hộp thoại "Tạo dự án"

    # Trang Tải lên chọn đúng dự án B làm nơi nhận file, header cũng ở B.
    at = run_view("upload", role="user", state={"_mock_db": db, "work_context": context})
    assert not at.exception
    assert at.selectbox(key="upload_project").value == project_b["id"]
    assert at.selectbox(key="header_quick_project_select").value == project_b["id"]

    # Tải file vào đúng dự án đó (cùng lời gọi API mà trang dùng) rồi áp dụng ngữ cảnh.
    result, error, db = call_api(
        "user",
        "upload_dataset",
        project_b["id"],
        "khach_hang.csv",
        CSV,
        "text/csv",
        state={"_mock_db": db},
    )
    assert error is None and result["dataset"]["project_id"] == project_b["id"]
    context.update(uploaded_dataset_context(result, project_b))

    at = run_view("overview", role="user", state={"_mock_db": db, "work_context": context})
    assert at.selectbox(key="header_quick_project_select").value == project_b["id"]
    assert at.session_state["work_context"]["project_id"] == project_b["id"]
    assert at.session_state["work_context"]["dataset_id"] == result["dataset"]["id"]
    in_a = [d for d in db["datasets"] if d["project_id"] == project_a["id"]]
    assert result["dataset"]["id"] not in {d["id"] for d in in_a}
