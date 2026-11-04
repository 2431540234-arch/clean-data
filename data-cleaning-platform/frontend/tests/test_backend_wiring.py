"""Nhóm 9: giao diện dùng các endpoint bổ sung (danh sách dataset, lỗi, dòng dữ liệu, điểm TB)."""

import pytest
import streamlit as st
from conftest import find_button

from components.labels import ACTION_LABELS, action_label, issue_type_label, severity_label

CONTEXT = {"work_context": {"dataset_id": 1}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


# ---------------------------------------------------------------- API (mock)


def test_list_project_datasets_newest_first_and_permissions(call_api):
    data, error, _ = call_api("user", "list_project_datasets", 1)
    assert error is None and [d["id"] for d in data] == [1]
    _, error, _ = call_api("user", "list_project_datasets", 3)  # project của admin
    assert error is not None and error.status_code == 403
    _, error, _ = call_api("user", "list_project_datasets", 999)
    assert error is not None and error.status_code == 404


def test_issues_need_profiling_then_list_with_severity(call_api):
    _, error, db = call_api("user", "get_issues", 1)
    assert error is not None and error.status_code == 404
    _, error, db = call_api("user", "run_profiling", 1, state={"_mock_db": db})
    issues, error, _ = call_api("user", "get_issues", 1, state={"_mock_db": db})
    assert error is None and issues
    expected = {"id", "column_name", "issue_type", "severity", "affected_count", "examples"}
    assert expected <= set(issues[0])
    severities = [i["severity"] for i in issues]
    order = {"high": 0, "medium": 1, "low": 2}
    assert severities == sorted(severities, key=order.get)


def test_suggestions_link_to_issue_ids(call_api):
    _, _, db = call_api("user", "run_profiling", 1)
    suggestions, _, db = call_api("user", "generate_suggestions", 1, state={"_mock_db": db})
    issues, _, _ = call_api("user", "get_issues", 1, state={"_mock_db": db})
    issue_ids = {i["id"] for i in issues}
    assert suggestions and all(s["issue_id"] in issue_ids for s in suggestions)


def test_get_rows_pages_and_validates(call_api):
    page, error, _ = call_api("user", "get_rows", 1, 1, 0, 10)
    assert error is None and page["total"] == 30 and len(page["rows"]) == 10
    assert page["columns"][0] == "ho_ten" and page["rows"][0]["row_index"] == 0
    last, _, _ = call_api("user", "get_rows", 1, 1, 25, 10)
    assert [r["row_index"] for r in last["rows"]] == [25, 26, 27, 28, 29]
    _, error, _ = call_api("user", "get_rows", 1, 999, 0, 10)
    assert error is not None and error.status_code == 404


def test_projects_have_dataset_count_and_optional_average(call_api):
    projects, _, db = call_api("user", "list_projects")
    by_id = {p["id"]: p for p in projects}
    assert by_id[1]["dataset_count"] == 1 and by_id[2]["dataset_count"] == 0
    assert by_id[1]["average_quality_score"] is None  # chưa có báo cáo -> ẩn
    _, _, db = call_api("user", "get_quality", 1, state={"_mock_db": db})
    projects, _, _ = call_api("user", "list_projects", state={"_mock_db": db})
    score = {p["id"]: p for p in projects}[1]["average_quality_score"]
    assert isinstance(score, float) and 0 < score <= 100


def test_change_password_returns_new_token(call_api):
    result, error, _ = call_api("user", "change_password", "User12345", "MatKhauMoi1")
    assert error is None and result["access_token"].startswith("mock-token-2")
    assert result["access_token"] != "mock-token-2"


# ---------------------------------------------------------------- nhãn nhật ký


@pytest.mark.parametrize(
    "code",
    [
        "auth.login",
        "auth.login_failed",
        "auth.register",
        "suggestion.generate",
        "dataset.select_sheet",
        "rule.create",
        "rule.delete",
    ],
)
def test_new_audit_codes_have_vietnamese_labels(code):
    assert code in ACTION_LABELS and action_label(code) != code


def test_unknown_codes_and_levels_fall_back_to_raw_text():
    assert action_label("moi.chua.co") == "moi.chua.co"
    assert severity_label("critical") == "critical"
    assert issue_type_label("la") == "la"


# ---------------------------------------------------------------- trang


def test_dashboard_shows_dataset_count_and_hides_missing_score(run_view):
    at = run_view("dashboard", role="user")
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Số dataset"] == "1" and "Điểm TB theo dự án" not in metrics
    assert any("1 dataset" in c.value for c in at.caption)


def test_dashboard_shows_average_score_when_available(run_view, call_api):
    _, _, db = call_api("user", "get_quality", 1)
    at = run_view("dashboard", role="user", state={"_mock_db": db})
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Điểm TB theo dự án"].endswith("/ 100")


def test_overview_lists_issues_with_severity(run_view):
    at = run_view("overview", role="user", state=CONTEXT)
    assert not at.exception
    issue_tables = [d.value for d in at.dataframe if "Loại lỗi" in d.value.columns]
    assert issue_tables, "tab Lỗi đã phát hiện phải có bảng lỗi"
    table = issue_tables[0]
    assert set(table["Mức độ"]) <= {"Cao", "Trung bình", "Thấp"}
    assert {"Cột", "Số dòng", "Ví dụ", "Mô tả"} <= set(table.columns)
    assert any("nhóm lỗi" in m.value for m in at.markdown)


def test_overview_keeps_working_when_issue_list_fails(run_view, monkeypatch):
    import api_client

    def broken(token, version_id):
        raise api_client.APIError(500, "hỏng")

    monkeypatch.setattr(api_client, "get_issues", broken)
    at = run_view("overview", role="user", state=CONTEXT)
    assert not at.exception
    assert any("Chưa lấy được danh sách lỗi" in w.value for w in at.warning)
    assert {m.label for m in at.metric} >= {"Số dòng", "Điểm chất lượng"}


def test_suggestion_cards_show_severity(run_view):
    at = run_view("suggestions", role="user", state=CONTEXT)
    find_button(at, "Sinh gợi ý").click().run()
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Mức độ" in html


def test_account_adopts_new_token_stays_logged_in_with_toast(run_view):
    at = run_view("account", role="user")
    at.text_input[0].set_value("User12345")
    at.text_input[1].set_value("MatKhauMoi1")
    at.text_input[2].set_value("MatKhauMoi1")
    find_button(at, "Đổi mật khẩu").click().run()
    assert not at.exception and not at.error
    assert at.session_state["access_token"] == "mock-token-2.1"  # token mới được nhận
    assert at.session_state["current_user"]["email"] == "user@example.com"
    assert any("Đã đổi mật khẩu" in t.value for t in at.toast)
    assert at.title[0].value == "Tài khoản"  # vẫn ở trang, chưa bị đăng xuất
