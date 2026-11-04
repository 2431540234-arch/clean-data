"""Trang chủ và dự án: trạng thái, quyền, bộ lọc và thao tác."""

import pytest
import streamlit as st
from conftest import find_button

import api_client
import mock_api


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    """AppTest chạy từng trang riêng lẻ nên không có trang đích để chuyển tới."""
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _card_titles(at):
    return [
        m.value.strip("*") for m in at.markdown if m.value.startswith("**") and "_" not in m.value
    ]


def _names(at):
    return {m.value.strip("*") for m in at.markdown if m.value.startswith("**")}


def test_user_sees_only_own_projects(run_view):
    at = run_view("dashboard", role="user")
    assert not at.exception
    names = _names(at)
    assert {"Khách hàng 2026", "Đơn hàng quý 3"} <= names
    assert "Dữ liệu nội bộ" not in names  # project của admin


def test_admin_sees_all_projects_and_project_kpis(run_view):
    at = run_view("dashboard", role="admin")
    assert {"Khách hàng 2026", "Đơn hàng quý 3", "Dữ liệu nội bộ"} <= _names(at)
    assert "Số dự án" in [m.label for m in at.metric]


def test_kpi_counts_projects(run_view):
    at = run_view("dashboard", role="user")
    values = {m.label: m.value for m in at.metric}
    assert values["Số dự án"] == "2"
    assert values["Số dataset"] == "1"


def test_empty_state_has_create_action(run_view):
    db = mock_api._seed()
    db["projects"] = []
    at = run_view("dashboard", role="user", state={"_mock_db": db})
    assert not at.exception
    assert any("Chưa có dự án nào" in m.value for m in at.markdown)
    assert any(b.label == "Tạo dự án đầu tiên" for b in at.button)


def test_api_error_shows_friendly_state_with_retry(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "list_projects", boom)
    at = run_view("dashboard", role="user")
    assert not at.exception
    assert "chưa sẵn sàng" in " ".join(e.value for e in at.error)
    assert any(b.label == "Thử lại" for b in at.button)


def test_open_project_sets_work_context(run_view):
    at = run_view("dashboard", role="user")
    next(b for b in at.button if b.key == "open_2").click().run()
    ctx = at.session_state["work_context"]
    assert ctx["project_id"] == 2 and ctx["project_name"] == "Đơn hàng quý 3"
    assert ctx["dataset_id"] is None
    assert ctx["rule_queue"] == [] and ctx["preview"] is None


def test_project_search_filters_cards(run_view):
    at = run_view("dashboard", role="user")
    at.text_input(key="project_search").set_value("Đơn hàng").run()
    names = _names(at)
    assert "Đơn hàng quý 3" in names
    assert "Khách hàng 2026" not in names


def test_recent_filter_limits_project_cards(run_view):
    db = mock_api._seed()
    db["projects"].extend(
        {
            "id": project_id,
            "name": f"Dự án mới {project_id}",
            "owner_id": 1,
            "created_at": f"2026-10-{project_id:02}T00:00:00+00:00",
        }
        for project_id in range(4, 10)
    )
    at = run_view("dashboard", role="admin", state={"_mock_db": db})
    at.radio(key="project_scope").set_value("Gần đây").run()
    names = _names(at)
    assert "Dự án mới 9" in names
    assert "Khách hàng 2026" not in names


def test_open_dataset_sets_version_and_clears_stale_queue(run_view):
    at = run_view(
        "dashboard",
        role="user",
        state={
            "work_context": {
                "project_id": 1,
                "project_name": "Khách hàng 2026",
                "rule_queue": [{"op": "drop_duplicates", "params": {}}],
                "preview": {"signature": "old"},
            }
        },
    )
    at.button(key="open_dataset_1").click().run()
    context = at.session_state["work_context"]
    assert context["dataset_id"] == 1
    assert context["version_id"] == 1
    assert context["rule_queue"] == [] and context["preview"] is None


def test_create_button_opens_dialog(run_view):
    at = run_view("dashboard", role="user")
    find_button(at, "Tạo dự án").click().run()
    assert "Tên dự án" in [t.label for t in at.text_input]


def test_rename_via_popover(run_view):
    at = run_view("dashboard", role="user")
    at.text_input(key="name_1").set_value("Tên mới")
    at.button(key="rename_1").click().run()
    projects = {p["id"]: p for p in at.session_state["_mock_db"]["projects"]}
    assert projects[1]["name"] == "Tên mới"


def test_rename_rejects_blank_name(run_view):
    at = run_view("dashboard", role="user")
    at.text_input(key="name_1").set_value("   ")
    at.button(key="rename_1").click().run()
    assert any("Vui lòng nhập tên dự án" in e.value for e in at.error)


def test_api_create_rename_delete(call_api):
    project, error, db = call_api("user", "create_project", "Sổ cái 2026")
    assert error is None and project["owner_id"] == 2 and project["name"] == "Sổ cái 2026"
    assert any(p["name"] == "Sổ cái 2026" for p in db["projects"])

    _, error, db = call_api("user", "delete_project", 2)
    assert error is None and 2 not in {p["id"] for p in db["projects"]}


def test_api_permissions_and_validation(call_api):
    _, error, _ = call_api("user", "delete_project", 3)  # project của admin
    assert error.status_code == 403
    _, error, _ = call_api("user", "update_project", 999, "x")
    assert error.status_code == 404
    _, error, _ = call_api("user", "create_project", "   ")
    assert error.status_code == 422
    _, error, _ = call_api("admin", "update_project", 1, "Admin đổi tên")  # admin sửa được của user
    assert error is None


def test_home_greets_user_and_lists_six_steps(run_view):
    at = run_view("home", role="user")
    assert not at.exception
    assert at.title[0].value == "Xin chào, Người dùng user"
    assert len([b for b in at.button if b.key and b.key.startswith("home_open_")]) == 6
    assert any("Chưa có dữ liệu đang làm việc" in m.value for m in at.markdown)


def test_home_shows_current_dataset(run_view):
    ctx = {"dataset_id": 7, "dataset_name": "khach_hang.csv", "project_name": "Khách hàng 2026"}
    at = run_view("home", role="user", state={"work_context": ctx})
    assert any("khach_hang.csv" in m.value for m in at.markdown)
    assert any(b.label == "Tiếp tục" for b in at.button)


def test_home_shows_real_project_datasets_and_recent_activity(run_view):
    at = run_view("home", role="user", state={"work_context": {"project_id": 1}})
    assert not at.exception
    assert any("Dataset gần đây" in item.value for item in at.markdown)
    assert any("Hoạt động gần đây" in item.value for item in at.markdown)
    assert len(at.dataframe) == 2
    assert "Tên file" in at.dataframe[0].value.columns
    assert "Hành động" in at.dataframe[1].value.columns


def test_kpi_tiles_are_a_single_list(run_view):
    """Thẻ KPI sinh từ một danh sách: thêm thẻ mới không đổi bố cục."""
    at = run_view("dashboard", role="admin")
    assert [m.label for m in at.metric] == [
        "Số dự án",
        "Số dataset",
    ]
