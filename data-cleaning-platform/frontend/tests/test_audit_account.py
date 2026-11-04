"""Bước 5: Nhật ký hoạt động (hook ghi log của mock + trang) và trang Tài khoản."""

from datetime import date

import pytest
import streamlit as st
from conftest import error_text, find_button, find_input

import api_client
import mock_api

STEP = {"op": "drop_duplicates", "column": None, "params": {}}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _actions(logs):
    return [log["action"] for log in logs]


# ---------------------------------------------------------------- hook ghi log của mock


def test_api_audit_me_returns_own_logs_newest_first(call_api):
    logs, error, _ = call_api("user", "audit_me")
    assert error is None
    assert _actions(logs) == ["project.create", "dataset.upload", "project.create"]
    assert {log["user_id"] for log in logs} == {2}
    times = [log["created_at"] for log in logs]
    assert times == sorted(times, reverse=True)


def test_api_actions_are_recorded(call_api):
    _, _, db = call_api("user", "apply_rules", 1, [STEP])
    _, _, db = call_api("user", "undo_version", 1, state={"_mock_db": db})
    _, _, db = call_api("user", "redo_version", 1, state={"_mock_db": db})
    _, _, db = call_api("user", "restore_version", 1, 1, state={"_mock_db": db})
    project, _, db = call_api("user", "create_project", "Mới", state={"_mock_db": db})
    _, _, db = call_api("user", "update_project", project["id"], "Đổi tên", state={"_mock_db": db})
    _, _, db = call_api("user", "delete_project", project["id"], state={"_mock_db": db})
    _, _, db = call_api(
        "user", "change_password", "User12345", "MatKhauMoi1", state={"_mock_db": db}
    )
    logs, _, _ = call_api("user", "audit_me", state={"_mock_db": db})
    recorded = _actions(logs)[:8][::-1]  # cũ -> mới
    assert recorded == [
        "version.apply_rule",
        "version.undo",
        "version.redo",
        "version.restore",
        "project.create",
        "project.update",
        "project.delete",
        "auth.change_password",
    ]
    apply_log = next(log for log in logs if log["action"] == "version.apply_rule")
    assert apply_log["old_value"] == {"version_number": 1}
    assert apply_log["new_value"]["version_number"] == 2 and apply_log["project_id"] == 1


def test_api_failed_actions_are_not_recorded(call_api):
    _, error, db = call_api("user", "apply_rules", 1, [])  # rule rỗng bị từ chối
    assert error is not None
    logs, _, _ = call_api("user", "audit_me", state={"_mock_db": db})
    assert len(logs) == 3  # chỉ còn các dòng seed


def test_api_audit_all_is_admin_only_and_contains_everyone(call_api):
    _, error, _ = call_api("user", "audit_all")
    assert error.status_code == 403
    logs, error, _ = call_api("admin", "audit_all")
    assert error is None and {log["user_id"] for log in logs} == {1, 2}


# ---------------------------------------------------------------- trang Nhật ký


def test_user_sees_only_own_logs_and_no_scope_toggle(run_view):
    at = run_view("audit", role="user")
    assert not at.exception
    assert not at.toggle  # user thường không có công tắc toàn hệ thống
    table = at.dataframe[0].value
    assert list(table["Hành động"]) == ["Tạo project", "Tải lên dataset", "Tạo project"]
    assert "Người thực hiện" not in table.columns
    assert "Hiển thị 1–3 trên 3 bản ghi" in " ".join(c.value for c in at.caption)


def test_admin_scope_toggle_shows_everyone_with_names(run_view):
    at = run_view("audit", role="admin")
    assert len(at.dataframe[0].value) == 1  # admin chỉ có 1 dòng của mình
    at.toggle(key="audit_everyone").set_value(True).run()
    table = at.dataframe[0].value
    assert len(table) == 4
    assert set(table["Người thực hiện"]) == {"Nguyễn Thị Minh Anh", "Trần Quốc Bảo"}


def test_filter_by_action(run_view):
    at = run_view("audit", role="user")
    at.selectbox(key="audit_actions").set_value("dataset.upload").run()
    table = at.dataframe[0].value
    assert list(table["Hành động"]) == ["Tải lên dataset"]
    assert "Hiển thị 1–1 trên 1 bản ghi (đã lọc từ 3)" in " ".join(c.value for c in at.caption)


def test_filter_by_date_range_and_no_match(run_view):
    at = run_view("audit", role="user")
    at.date_input(key="audit_from").set_value(date(2026, 9, 12)).run()
    at.date_input(key="audit_to").set_value(date(2026, 9, 12)).run()
    assert len(at.dataframe[0].value) == 2  # 2 dòng ngày 12/09/2026
    at.date_input(key="audit_from").set_value(date(2020, 1, 1)).run()
    at.date_input(key="audit_to").set_value(date(2020, 1, 2)).run()
    assert any("Không có bản ghi nào khớp bộ lọc" in i.value for i in at.info)


def test_filter_with_only_one_date_bound(run_view):
    at = run_view("audit", role="user")
    at.date_input(key="audit_from").set_value(date(2026, 10, 1)).run()
    assert list(at.dataframe[0].value["Hành động"]) == ["Tạo project"]  # chỉ dòng ngày 05/10
    at.date_input(key="audit_from").set_value(date(2020, 1, 1)).run()
    at.date_input(key="audit_to").set_value(date(2026, 9, 30)).run()
    assert len(at.dataframe[0].value) == 2


def test_clear_filters_button_restores_full_list(run_view):
    at = run_view("audit", role="user")
    at.selectbox(key="audit_actions").set_value("dataset.upload").run()
    assert len(at.dataframe[0].value) == 1
    find_button(at, "Xóa bộ lọc").click().run()
    assert not at.exception and len(at.dataframe[0].value) == 3


def test_admin_can_filter_everyone_by_user_name_or_email(run_view):
    at = run_view("audit", role="admin")
    at.toggle(key="audit_everyone").set_value(True).run()
    at.text_input(key="audit_user").set_value("quốc bảo").run()
    assert set(at.dataframe[0].value["Người thực hiện"]) == {"Trần Quốc Bảo"}
    at.text_input(key="audit_user").set_value("khong.ai.ca").run()
    assert any("Không có bản ghi nào khớp bộ lọc" in i.value for i in at.info)


def test_pagination_splits_long_logs_into_pages(run_view):
    db = mock_api._seed()
    template = db["audit"][0]
    db["audit"] = [{**template, "id": 1000 + i} for i in range(45)]
    at = run_view("audit", role="user", state={"_mock_db": db})
    assert len(at.dataframe[0].value) == 20
    assert "Hiển thị 1–20 trên 45 bản ghi" in " ".join(c.value for c in at.caption)
    assert find_button(at, "Trước").disabled and not find_button(at, "Sau").disabled
    find_button(at, "Sau").click().run()
    find_button(at, "Sau").click().run()
    assert len(at.dataframe[0].value) == 5
    assert "Hiển thị 41–45 trên 45 bản ghi" in " ".join(c.value for c in at.caption)
    assert find_button(at, "Sau").disabled and not find_button(at, "Trước").disabled


def test_detail_shows_before_and_after(run_view):
    at = run_view("audit", role="user")
    assert not at.code  # chưa chọn bản ghi nào
    audit = at.session_state["_mock_db"]["audit"]
    upload_id = next(log["id"] for log in audit if log["action"] == "dataset.upload")
    at.selectbox(key="audit_detail").set_value(upload_id).run()
    assert len(at.code) == 2
    assert (
        '"filename": "khach_hang_ban.csv"' in at.code[1].value and '"rows": 30' in at.code[1].value
    )


def test_empty_state_for_user_without_activity(run_view):
    db = mock_api._seed()
    db["audit"] = []
    at = run_view("audit", role="user", state={"_mock_db": db})
    assert any("Chưa có hoạt động nào" in m.value for m in at.markdown)
    assert any(b.label == "Tải dữ liệu lên" for b in at.button)


def test_audit_error_state(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "audit_me", boom)
    at = run_view("audit", role="user")
    assert not at.exception and any(b.label == "Thử lại" for b in at.button)


def test_unknown_action_code_is_shown_verbatim(run_view):
    db = mock_api._seed()
    db["audit"][1]["action"] = "dataset.mot_hanh_dong_moi"
    at = run_view("audit", role="user", state={"_mock_db": db})
    assert "dataset.mot_hanh_dong_moi" in list(at.dataframe[0].value["Hành động"])


# ---------------------------------------------------------------- trang Tài khoản


def _submit_password(at, old, new, confirm):
    find_input(at, "Mật khẩu hiện tại").set_value(old)
    find_input(at, "Mật khẩu mới").set_value(new)
    find_input(at, "Nhập lại mật khẩu mới").set_value(confirm)
    find_button(at, "Đổi mật khẩu").click().run()
    return at


def test_account_shows_profile_from_server(run_view):
    at = run_view("account", role="user")
    assert not at.exception
    html = " ".join(m.value for m in at.markdown)
    assert "Nguyễn Thị Minh Anh" in html and "user@example.com" in html
    assert "Người dùng" in html and "Đang hoạt động" in html
    assert any("Tham gia từ 01/09/2026" in c.value for c in at.caption)


def test_account_shows_usage_tiles_and_read_only_personal_info(run_view):
    at = run_view("account", role="user")
    assert not at.exception
    tiles = {m.label: m.value for m in at.metric}
    assert tiles["Dự án"] == "2" and tiles["Dataset"] == "1" and "Quy tắc của tôi" in tiles
    captions = [c.value for c in at.caption]
    assert "Họ và tên" in captions and "Email" in captions
    markdown = [m.value for m in at.markdown]
    assert "**Nguyễn Thị Minh Anh**" in markdown and "**user@example.com**" in markdown
    assert not {"Họ và tên", "Email"} & {t.label for t in at.text_input}  # chỉ xem, không sửa
    assert not any("Lưu thay đổi" in b.label for b in at.button)  # backend chưa có cập nhật hồ sơ
    assert any("phiên đăng nhập khác sẽ hết hiệu lực" in i.value for i in at.info)


def test_account_hides_usage_tiles_when_projects_fail(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "lỗi")

    monkeypatch.setattr(api_client, "list_projects", boom)
    at = run_view("account", role="user")
    assert not at.exception and not at.metric


def test_account_admin_badge(run_view):
    at = run_view("account", role="admin")
    assert "Quản trị viên" in " ".join(m.value for m in at.markdown)


@pytest.mark.parametrize(
    ("old", "new", "confirm", "message"),
    [
        ("", "MatKhauMoi1", "MatKhauMoi1", "nhập mật khẩu hiện tại"),
        ("User12345", "ngan", "ngan", "ít nhất 8 ký tự"),
        ("User12345", "User12345", "User12345", "phải khác mật khẩu hiện tại"),
        ("User12345", "MatKhauMoi1", "KhacNhau123", "không khớp"),
    ],
)
def test_change_password_client_validation(run_view, old, new, confirm, message):
    at = _submit_password(run_view("account", role="user"), old, new, confirm)
    assert message in error_text(at)
    assert at.session_state["_mock_db"]["users"][1]["password"] == "User12345"  # chưa đổi


def test_change_password_wrong_current_password(run_view):
    at = _submit_password(
        run_view("account", role="user"), "SaiMatKhau1", "MatKhauMoi1", "MatKhauMoi1"
    )
    assert "Mật khẩu cũ không đúng." in error_text(at)
    assert at.session_state["_mock_db"]["users"][1]["password"] == "User12345"


def test_change_password_success(run_view):
    at = _submit_password(
        run_view("account", role="user"), "User12345", "MatKhauMoi1", "MatKhauMoi1"
    )
    assert not at.exception and not at.error
    assert at.session_state["_mock_db"]["users"][1]["password"] == "MatKhauMoi1"
    assert any("Đã đổi mật khẩu" in t.value for t in at.toast)
    assert at.session_state["access_token"].startswith("mock-token-2")  # vẫn đăng nhập (token mới)


def test_change_password_connection_error_is_friendly(run_view, monkeypatch):
    at = run_view("account", role="user")
    monkeypatch.setattr(api_client, "MOCK", False)
    monkeypatch.setattr(api_client, "BACKEND_URL", "http://127.0.0.1:9")
    _submit_password(at, "User12345", "MatKhauMoi1", "MatKhauMoi1")
    assert not at.exception and "Không kết nối được tới máy chủ" in error_text(at)


def test_account_falls_back_to_cached_profile_when_refresh_fails(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "get_me", boom)
    at = run_view("account", role="user")
    assert not at.exception
    assert any("đang hiển thị thông tin đã lưu" in w.value for w in at.warning)
    assert any(b.label == "Đổi mật khẩu" for b in at.button)


def test_account_expired_session_prompts_login(run_view, monkeypatch):
    def expired(token):
        raise api_client.APIError(401, "Token không hợp lệ hoặc đã hết hạn.")

    monkeypatch.setattr(api_client, "get_me", expired)
    at = run_view("account", role="user")
    assert any(b.label == "Đăng nhập lại" for b in at.button)
