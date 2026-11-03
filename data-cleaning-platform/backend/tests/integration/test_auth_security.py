"""Nhóm 8 - bảo mật xác thực: chặn đăng nhập sai (429), nhật ký, đổi mật khẩu, thu hồi token."""

import time

from sqlalchemy import select

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.user import User


def _register(client, email="a@example.com", password="Password123"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Người Dùng"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _login(client, email="a@example.com", password="Password123"):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def _actions(db, action):
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id)))


# ---------------------------------------------------------------- đăng ký


def test_email_is_case_insensitive_for_register_and_login(client):
    _register(client, "Nguyen.An@Example.COM")
    assert _login(client, "nguyen.an@example.com").status_code == 200
    assert _login(client, "NGUYEN.AN@EXAMPLE.COM").status_code == 200
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "nguyen.an@example.com", "password": "Password123", "full_name": "B"},
    )
    assert duplicate.status_code == 409


def test_register_rejects_bad_input(client):
    cases = [
        {"email": "khong-phai-email", "password": "Password123", "full_name": "A"},
        {"email": "ok@example.com", "password": "ngan", "full_name": "A"},
        {"email": "ok@example.com", "password": "Password123", "full_name": ""},
        {"email": "ok@example.com", "password": "x" * 200, "full_name": "A"},
    ]
    for body in cases:
        assert client.post("/api/v1/auth/register", json=body).status_code == 422


def test_register_cannot_choose_role(client, db):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "x@example.com",
            "password": "Password123",
            "full_name": "A",
            "role": "admin",
        },
    )
    assert db.scalars(select(User)).one().role == "user"


# ---------------------------------------------------------------- nhật ký đăng nhập


def test_login_success_and_failure_are_audited_without_password(client, db):
    _register(client)
    assert _login(client, password="SaiMatKhau").status_code == 401
    assert _login(client, "khong.co@example.com", "Password123").status_code == 401
    assert _login(client).status_code == 200

    failed = _actions(db, "auth.login_failed")
    assert [f.new_value["reason"] for f in failed] == ["wrong_password", "unknown_email"]
    assert failed[0].user_id is not None and failed[1].user_id is None
    assert _actions(db, "auth.login")[0].new_value == {"email": "a@example.com"}
    everything = " ".join(str(a.new_value) + str(a.old_value) for a in db.scalars(select(AuditLog)))
    assert "SaiMatKhau" not in everything and "Password123" not in everything
    assert _actions(db, "auth.register")


def test_generic_message_does_not_reveal_whether_email_exists(client):
    _register(client)
    wrong_password = _login(client, password="SaiMatKhau")
    unknown = _login(client, "khong.co@example.com")
    assert wrong_password.status_code == unknown.status_code == 401
    assert wrong_password.json() == unknown.json() == {"detail": "Email hoặc mật khẩu không đúng."}


# ---------------------------------------------------------------- chặn đăng nhập sai


def test_five_failures_lock_login_with_429(client, db):
    _register(client)
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        assert _login(client, password="SaiMatKhau").status_code == 401
    locked = _login(client, password="SaiMatKhau")
    assert locked.status_code == 429 and "sau 15 phút" in locked.json()["detail"]
    # đang bị khóa: ngay cả mật khẩu đúng cũng bị từ chối, và không ghi thêm dòng nào
    before = len(_actions(db, "auth.login_failed"))
    assert _login(client).status_code == 429
    assert len(_actions(db, "auth.login_failed")) == before


def test_successful_login_resets_the_counter(client):
    _register(client)
    for _ in range(settings.LOGIN_MAX_ATTEMPTS - 1):
        _login(client, password="SaiMatKhau")
    assert _login(client).status_code == 200
    # bộ đếm đã về 0: lại được sai thêm (MAX - 1) lần mà chưa bị khóa
    for _ in range(settings.LOGIN_MAX_ATTEMPTS - 1):
        assert _login(client, password="SaiMatKhau").status_code == 401
    assert _login(client).status_code == 200


def test_lock_is_per_email_and_old_failures_expire(client, db, monkeypatch):
    _register(client)
    _register(client, "b@example.com")
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        _login(client, password="SaiMatKhau")
    assert _login(client, "b@example.com").status_code == 200  # email khác không bị ảnh hưởng
    assert _login(client).status_code == 429
    monkeypatch.setattr(settings, "LOGIN_WINDOW_MINUTES", 0)  # cửa sổ thời gian đã trôi qua
    time.sleep(0.05)
    assert _login(client).status_code == 200


def test_ip_wide_cap_stops_guessing_with_many_emails(client, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_MAX_ATTEMPTS_PER_IP", 4)
    for i in range(4):
        assert _login(client, f"nguoi{i}@example.com").status_code == 401
    assert _login(client, "nguoi-moi@example.com").status_code == 429


def test_email_key_is_case_insensitive_for_lockout(client):
    _register(client)
    for i in range(settings.LOGIN_MAX_ATTEMPTS):
        _login(client, ["A@example.com", "a@EXAMPLE.com"][i % 2], "SaiMatKhau")
    assert _login(client).status_code == 429


# ---------------------------------------------------------------- khóa tài khoản


def test_locked_account_cannot_login_and_old_token_is_rejected(client, db):
    token = _register(client)
    user = db.scalars(select(User)).one()
    user.is_active = False
    db.commit()
    assert _login(client).status_code == 401
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 401


# ---------------------------------------------------------------- đổi mật khẩu


def test_change_password_flow_revokes_old_tokens_and_returns_new_one(client, db):
    old_token = _register(client)
    time.sleep(1.1)  # iat tính theo giây: tách rõ token cũ và thời điểm đổi mật khẩu
    headers = {"Authorization": f"Bearer {old_token}"}
    response = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Password123", "new_password": "MatKhauMoi456"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message"] == "Đã đổi mật khẩu." and body["token_type"] == "bearer"

    revoked = client.get("/api/v1/auth/me", headers=headers)
    assert revoked.status_code == 401 and "hết hiệu lực" in revoked.json()["detail"]
    fresh = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert fresh.status_code == 200
    assert _login(client, password="Password123").status_code == 401
    assert _login(client, password="MatKhauMoi456").status_code == 200
    log = _actions(db, "auth.change_password")[0]
    assert "MatKhauMoi456" not in str(log.new_value) + str(log.old_value)


def test_change_password_validation(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    url = "/api/v1/auth/change-password"
    wrong = client.post(
        url, json={"old_password": "Sai", "new_password": "MatKhauMoi456"}, headers=headers
    )
    assert wrong.status_code == 401 and wrong.json()["detail"] == "Mật khẩu cũ không đúng."
    same = client.post(
        url, json={"old_password": "Password123", "new_password": "Password123"}, headers=headers
    )
    assert same.status_code == 422
    short = client.post(
        url, json={"old_password": "Password123", "new_password": "ngan"}, headers=headers
    )
    assert short.status_code == 422
    assert (
        client.post(url, json={"old_password": "a", "new_password": "bbbbbbbb"}).status_code == 401
    )


def test_change_password_wrong_old_password_is_throttled(client):
    token = _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    url = "/api/v1/auth/change-password"
    body = {"old_password": "Sai", "new_password": "MatKhauMoi456"}
    for _ in range(settings.LOGIN_MAX_ATTEMPTS):
        assert client.post(url, json=body, headers=headers).status_code == 401
    assert client.post(url, json=body, headers=headers).status_code == 429
    good = {"old_password": "Password123", "new_password": "MatKhauMoi456"}
    assert client.post(url, json=good, headers=headers).status_code == 429
