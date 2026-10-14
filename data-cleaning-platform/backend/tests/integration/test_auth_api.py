"""Test thật cho API đăng ký/đăng nhập/lấy thông tin bản thân."""

from fastapi.testclient import TestClient


def test_register_creates_user_with_user_role(client: TestClient) -> None:
    """Đăng ký phải luôn tạo role 'user', trả về access token hợp lệ."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Password123", "full_name": "Nguoi Moi"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_fails(client: TestClient) -> None:
    """Đăng ký với email đã tồn tại phải trả lỗi 409."""
    payload = {"email": "dup@example.com", "password": "Password123", "full_name": "Nguoi Dung"}
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 200

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_login_and_get_me(client: TestClient) -> None:
    """Đăng nhập thành công phải cho phép gọi /auth/me với token trả về."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "Password123", "full_name": "Nguoi Dung"},
    )

    login_response = client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "Password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["email"] == "login@example.com"
    assert me_body["role"] == "user"


def test_login_wrong_password_fails(client: TestClient) -> None:
    """Đăng nhập với mật khẩu sai phải trả lỗi 401."""
    client.post(
        "/api/v1/auth/register",
        json={"email": "wrongpass@example.com", "password": "Password123", "full_name": "A"},
    )

    response = client.post(
        "/api/v1/auth/login", json={"email": "wrongpass@example.com", "password": "SaiMatKhau"}
    )
    assert response.status_code == 401
