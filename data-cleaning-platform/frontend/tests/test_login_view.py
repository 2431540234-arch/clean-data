"""Trang Đăng nhập/Đăng ký: kiểm tra dữ liệu, thông báo lỗi, đăng nhập/đăng ký thành công."""

import pytest
from conftest import error_text, find_button, find_input

import api_client
import mock_api

GENERIC_FAILURE = "Email hoặc mật khẩu không đúng."


def _login(at, email, password):
    find_input(at, "Email").set_value(email)
    find_input(at, "Mật khẩu").set_value(password)
    find_button(at, "Đăng nhập").click().run()
    return at


def _register(at, name, email, password, confirm):
    find_input(at, "Họ và tên").set_value(name)
    find_input(at, "Email", 1).set_value(email)
    find_input(at, "Mật khẩu", 1).set_value(password)
    find_input(at, "Nhập lại mật khẩu").set_value(confirm)
    find_button(at, "Tạo tài khoản").click().run()
    return at


def test_renders_brand_tabs_and_mock_banner(run_view):
    at = run_view("login")
    assert not at.exception
    assert [t.label for t in at.tabs] == ["Đăng nhập", "Đăng ký"]
    html = " ".join(m.value for m in at.markdown)
    assert "Data Cleaning Platform" in html
    assert "Chế độ dữ liệu mẫu" in html and "admin@example.com" in html


def test_login_empty_form_lists_problems(run_view):
    at = run_view("login")
    find_button(at, "Đăng nhập").click().run()
    assert "Vui lòng nhập email" in error_text(at)
    assert "Vui lòng nhập mật khẩu" in error_text(at)
    assert at.session_state["access_token"] is None


def test_login_invalid_email_format(run_view):
    at = _login(run_view("login"), "abc", "x")
    assert "Email không hợp lệ" in error_text(at)


def test_login_success_stores_session_and_shows_toast(run_view):
    at = _login(run_view("login"), "user@example.com", "User12345")
    assert at.session_state["access_token"] == "mock-token-2"
    assert at.session_state["current_user"]["email"] == "user@example.com"
    assert any("Đăng nhập thành công" in t.value for t in at.toast)


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("user@example.com", "sai-mat-khau"),  # email tồn tại, sai mật khẩu
        ("khong-ton-tai@example.com", "User12345"),  # email không tồn tại
    ],
)
def test_login_failure_message_is_generic(run_view, email, password):
    at = _login(run_view("login"), email, password)
    assert error_text(at).strip() == GENERIC_FAILURE
    assert at.session_state["access_token"] is None


def test_login_failure_does_not_reveal_locked_account(run_view):
    db = mock_api._seed()
    next(u for u in db["users"] if u["id"] == 2)["is_active"] = False
    at = _login(run_view("login", state={"_mock_db": db}), "user@example.com", "User12345")
    assert error_text(at).strip() == GENERIC_FAILURE
    assert "khóa" not in error_text(at)


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_login_failure_hides_backend_wording(run_view, monkeypatch, status):
    """Dù backend trả lời lẽ lộ thông tin, giao diện chỉ hiện câu chung."""

    def fake_login(email, password):
        raise api_client.APIError(status, "Email này không tồn tại trong hệ thống.")

    monkeypatch.setattr(api_client, "login", fake_login)
    at = _login(run_view("login"), "bat-ky@example.com", "bat-ky-mat-khau")
    assert error_text(at).strip() == GENERIC_FAILURE


def test_register_validation(run_view):
    at = run_view("login")
    _register(at, "", "", "", "")
    assert "họ và tên" in error_text(at) and "email" in error_text(at)
    assert "ít nhất 8" in error_text(at)
    _register(at, "A", "a@b.co", "MatKhau123", "Khac")
    assert "không khớp" in error_text(at)
    assert at.session_state["access_token"] is None


def test_register_duplicate_email_keeps_backend_message(run_view):
    at = _register(run_view("login"), "A", "user@example.com", "MatKhau123", "MatKhau123")
    assert "Email đã được sử dụng." in error_text(at)
    assert at.session_state["access_token"] is None


def test_register_success(run_view):
    at = _register(
        run_view("login"), "  Lê Văn Hùng ", "hung@example.com", "MatKhau123", "MatKhau123"
    )
    assert at.session_state["current_user"]["full_name"] == "Lê Văn Hùng"
    assert at.session_state["current_user"]["role"] == "user"
    assert any("Tạo tài khoản thành công" in t.value for t in at.toast)


def test_connection_error_is_friendly_with_retry(run_view, monkeypatch):
    monkeypatch.setattr(api_client, "MOCK", False)
    monkeypatch.setattr(api_client, "BACKEND_URL", "http://127.0.0.1:9")  # cổng đóng
    at = _login(run_view("login"), "user@example.com", "User12345")
    assert not at.exception
    assert "Không kết nối được tới máy chủ" in error_text(at)
    assert any(b.label == "Thử lại" for b in at.button)
