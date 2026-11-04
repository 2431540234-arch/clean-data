"""Bước 6: API quản trị của mock, trang Quản trị người dùng và Thống kê hệ thống."""

import pytest
import streamlit as st
from conftest import error_text

import api_client
from components.user_table import user_matches

ADMIN = {"id": 1, "full_name": "Trần Quốc Bảo", "email": "admin@example.com"}


@pytest.fixture(autouse=True)
def _no_page_switch(monkeypatch):
    monkeypatch.setattr(st, "switch_page", lambda page: None)


def _user(db, user_id):
    return next(u for u in db["users"] if u["id"] == user_id)


# ---------------------------------------------------------------- logic lọc


def _sample_user(**changes):
    return {
        "id": 5, "full_name": "Lê Văn Hùng", "email": "hung@example.com",
        "role": "user", "is_active": True, **changes,
    }  # fmt: skip


def test_user_matches_search_role_and_status():
    user = _sample_user()
    assert user_matches(user, "", None, None)
    assert user_matches(user, "  hùng ", None, None)  # không phân biệt hoa thường, bỏ khoảng trắng
    assert user_matches(user, "HUNG@EXAMPLE", None, None)
    assert not user_matches(user, "khác", None, None)
    assert not user_matches(user, "", "admin", None)
    assert not user_matches(user, "", None, False)
    assert user_matches(_sample_user(is_active=False), "", "user", False)


# ---------------------------------------------------------------- API (mock)


def test_api_admin_endpoints_require_admin(call_api):
    for name, args in [
        ("admin_list_users", ()),
        ("admin_update_user", (2,)),
        ("admin_reset_password", (2,)),
        ("admin_stats", ()),
    ]:
        _, error, _ = call_api("user", name, *args)
        assert error.status_code == 403, name


def test_api_update_role_and_lock_with_audit(call_api):
    updated, error, db = call_api("admin", "admin_update_user", 2, role="admin")
    assert error is None and updated["role"] == "admin" and "password" not in updated
    updated, _, db = call_api(
        "admin", "admin_update_user", 2, is_active=False, state={"_mock_db": db}
    )
    assert updated["is_active"] is False
    updated, _, db = call_api(
        "admin", "admin_update_user", 2, is_active=True, state={"_mock_db": db}
    )
    logs, _, _ = call_api("admin", "audit_all", state={"_mock_db": db})
    recorded = [log["action"] for log in logs][:3][::-1]
    assert recorded == ["user.change_role", "user.lock", "user.unlock"]
    lock = next(log for log in logs if log["action"] == "user.lock")
    assert lock["entity_type"] == "user" and lock["entity_id"] == 2 and lock["user_id"] == 1
    assert lock["old_value"] == {"is_active": True} and lock["new_value"] == {"is_active": False}


def test_api_noop_update_writes_no_audit(call_api):
    _, error, db = call_api("admin", "admin_update_user", 2, role="user")  # đã là user
    assert error is None
    logs, _, _ = call_api("admin", "audit_all", state={"_mock_db": db})
    assert not any(log["action"].startswith("user.") for log in logs)


def test_api_update_validation_and_unknown_user(call_api):
    _, error, _ = call_api("admin", "admin_update_user", 2, role="superuser")
    assert error.status_code == 422 and "Quyền phải là" in error.detail
    _, error, _ = call_api("admin", "admin_update_user", 999, role="user")
    assert error.status_code == 404


def test_api_cannot_remove_or_lock_the_last_admin(call_api):
    _, error, _ = call_api("admin", "admin_update_user", 1, role="user")
    assert error.status_code == 422 and "quản trị viên cuối cùng" in error.detail
    _, error, _ = call_api("admin", "admin_update_user", 1, is_active=False)
    assert error.status_code == 422
    # có admin thứ hai thì hạ quyền được
    _, _, db = call_api("admin", "admin_update_user", 2, role="admin")
    _, error, _ = call_api("admin", "admin_update_user", 1, role="user", state={"_mock_db": db})
    assert error is None


def test_api_reset_password_returns_temporary_password(call_api):
    result, error, db = call_api("admin", "admin_reset_password", 2)
    assert error is None and result["new_password"].startswith("Tam")
    assert _user(db, 2)["password"] == result["new_password"] != "User12345"
    logs, _, _ = call_api("admin", "audit_all", state={"_mock_db": db})
    assert logs[0]["action"] == "user.reset_password" and logs[0]["entity_id"] == 2


def test_api_stats_reflect_state(call_api):
    stats, error, db = call_api("admin", "admin_stats")
    assert error is None
    assert stats == {
        "total_users": 2, "total_admins": 1, "active_users": 2, "total_projects": 3,
        "total_datasets": 1, "total_ai_calls": 0, "average_quality_score": 90.7,
    }  # fmt: skip
    _, _, db = call_api("user", "generate_suggestions", 1, state={"_mock_db": db})
    _, _, db = call_api("admin", "admin_update_user", 2, is_active=False, state={"_mock_db": db})
    stats, _, _ = call_api("admin", "admin_stats", state={"_mock_db": db})
    assert stats["total_ai_calls"] == 1 and stats["active_users"] == 1


# ---------------------------------------------------------------- trang Quản trị người dùng


def _open_users(run_view, **state):
    return run_view("admin_users", role="admin", state=state)


def _select(at, user_id):
    at.selectbox(key="admin_user_selected").set_value(user_id).run()
    return at


def test_user_cannot_open_admin_pages(run_view):
    for page in ("admin_users", "admin_stats"):
        at = run_view(page, role="user")
        assert "không có quyền" in error_text(at)


def test_users_page_lists_everyone_with_kpis(run_view):
    at = _open_users(run_view)
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {
        "Tổng người dùng": "2",
        "Quản trị viên": "1",
        "Đang hoạt động": "2",
        "Đã khóa": "0",
    }
    table = at.dataframe[0].value
    assert list(table["Họ tên"]) == ["Trần Quốc Bảo (bạn)", "Nguyễn Thị Minh Anh"]
    assert list(table["Quyền"]) == ["Quản trị viên", "Người dùng"]


def test_users_filters(run_view):
    at = _open_users(run_view)
    at.text_input(key="admin_user_query").set_value("minh anh").run()
    assert list(at.dataframe[0].value["Email"]) == ["user@example.com"]
    at.text_input(key="admin_user_query").set_value("").run()
    at.selectbox(key="admin_user_role_filter").set_value("Quản trị viên").run()
    assert len(at.dataframe[0].value) == 1
    at.selectbox(key="admin_user_status_filter").set_value("Đã khóa").run()
    assert any("Không có người dùng nào khớp bộ lọc" in i.value for i in at.info)


def test_manage_panel_for_other_user_offers_three_actions(run_view):
    at = _select(_open_users(run_view), 2)
    assert at.selectbox(key="role_2").value == "user"
    assert at.button(key="save_role_2").disabled  # chưa đổi quyền
    assert [b.label for b in at.button if b.key in {"toggle_active_2", "reset_2"}] == [
        "Khóa tài khoản",
        "Đặt lại mật khẩu",
    ]


def test_manage_panel_for_self_blocks_actions(run_view):
    at = _select(_open_users(run_view), ADMIN["id"])
    assert any("không thể tự khóa hay hạ quyền" in i.value for i in at.info)
    assert not [
        b for b in at.button if b.key and b.key.startswith(("save_role", "toggle", "reset"))
    ]


def test_change_role_after_confirmation(run_view):
    at = _select(_open_users(run_view), 2)
    at.selectbox(key="role_2").set_value("admin").run()
    assert not at.button(key="save_role_2").disabled
    at.session_state["save_role_2__confirmed"] = True  # mô phỏng bấm xác nhận trong hộp thoại
    at.run()
    assert not at.exception
    assert _user(at.session_state["_mock_db"], 2)["role"] == "admin"
    assert any("Đã đổi quyền" in t.value for t in at.toast)


def test_lock_and_unlock_after_confirmation(run_view):
    at = _select(_open_users(run_view), 2)
    at.session_state["toggle_active_2__confirmed"] = True
    at.run()
    assert _user(at.session_state["_mock_db"], 2)["is_active"] is False
    assert {m.label: m.value for m in at.metric}["Đã khóa"] == "1"
    assert any(b.label == "Mở khóa tài khoản" for b in at.button)
    assert [t for t in at.toast if "Đã khóa" in t.value]


def test_reset_password_shows_temporary_password_once(run_view):
    at = _select(_open_users(run_view), 2)
    at.session_state["reset_2__confirmed"] = True
    at.run()
    password = _user(at.session_state["_mock_db"], 2)["password"]
    assert at.code[0].value == password
    assert any("chỉ hiển thị một lần" in s.value for s in at.success)
    at.button(key="hide_reset_2").click().run()
    at.run()  # AppTest: lần chạy lại nội bộ của st.rerun() còn giữ trạng thái "đã bấm" của nút
    assert not at.code and at.session_state["work_context"]["reset_result"] is None


def test_action_failure_is_shown_inline(run_view, monkeypatch):
    at = _select(_open_users(run_view), 2)

    def refuse(token, user_id, **kwargs):
        raise api_client.APIError(422, "Không thể hạ quyền hoặc khóa quản trị viên cuối cùng.")

    monkeypatch.setattr(api_client, "admin_update_user", refuse)
    at.session_state["toggle_active_2__confirmed"] = True
    at.run()
    assert "quản trị viên cuối cùng" in error_text(at)
    assert _user(at.session_state["_mock_db"], 2)["is_active"] is True


def test_users_page_error_state(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "admin_list_users", boom)
    at = _open_users(run_view)
    assert not at.exception and any(b.label == "Thử lại" for b in at.button)


# ---------------------------------------------------------------- trang Thống kê hệ thống


def test_stats_page_shows_metrics_and_charts(run_view):
    at = run_view("admin_stats", role="admin")
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {
        "Tổng người dùng": "2",
        "Tổng dự án": "3",
        "Dataset": "1",
        "Lượt gọi AI": "0",
    }
    assert any("2 hoạt động · 0 bị khóa" in c.value for c in at.caption)
    assert len(at.get("plotly_chart")) == 3  # 2 biểu đồ vành khuyên + gauge
    html = " ".join(m.value for m in at.markdown)
    assert "90,7 / 100" in html and "Tốt" in html
    # chỉ hiện trường có trong schema /admin/stats: không biểu đồ theo ngày, không dịch vụ
    unsupported = ("Hoạt động hệ thống", "Tình trạng dịch vụ")
    assert not any(text in m.value for m in at.markdown for text in unsupported)


def test_stats_page_hides_quality_gauge_without_score(run_view, monkeypatch):
    stats = {
        "total_users": 2,
        "total_admins": 1,
        "active_users": 2,
        "total_projects": 0,
        "total_datasets": 0,
        "total_ai_calls": 0,
        "average_quality_score": None,
    }
    monkeypatch.setattr(api_client, "admin_stats", lambda token: stats)
    at = run_view("admin_stats", role="admin")
    assert not at.exception
    assert len(at.get("plotly_chart")) == 2
    assert any("Chưa có dataset nào được tính điểm" in c.value for c in at.caption)


def test_admin_pages_link_to_each_other(run_view):
    for page, other_label in (("admin_users", "Thống kê hệ thống"), ("admin_stats", "Người dùng")):
        at = run_view(page, role="admin")
        labels = [b.label for b in at.button] + [link.proto.label for link in at.get("page_link")]
        assert other_label in labels


def test_stats_page_error_state(run_view, monkeypatch):
    def boom(token):
        raise api_client.APIError(500, "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng.")

    monkeypatch.setattr(api_client, "admin_stats", boom)
    at = run_view("admin_stats", role="admin")
    assert not at.exception and any(b.label == "Thử lại" for b in at.button)
