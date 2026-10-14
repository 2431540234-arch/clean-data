"""Client gọi API backend bằng httpx, tự gắn JWT token (nếu có) vào header Authorization."""

import os
from typing import Any

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


class APIError(Exception):
    """Lỗi khi gọi API backend, giữ lại status_code và thông báo lỗi để hiển thị cho người dùng."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _headers(token: str | None) -> dict[str, str]:
    """Dựng header Authorization nếu có token."""
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def request(
    method: str,
    path: str,
    token: str | None = None,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> Any:
    """Gọi API backend tại BACKEND_URL + path, raise APIError nếu status không phải 2xx.

    Args:
        method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE".
        path: đường dẫn API, ví dụ "/api/v1/auth/login".
        token: JWT access token, nếu có sẽ gắn vào header Authorization.
    """
    url = f"{BACKEND_URL}{path}"
    with httpx.Client(timeout=timeout) as client:
        response = client.request(
            method, url, headers=_headers(token), json=json, params=params, files=files
        )

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise APIError(response.status_code, str(detail))

    if response.content:
        return response.json()
    return None


def login(email: str, password: str) -> dict[str, Any]:
    """Đăng nhập, trả về {"access_token": ..., "token_type": "bearer"}."""
    return request("POST", "/api/v1/auth/login", json={"email": email, "password": password})


def register(email: str, password: str, full_name: str) -> dict[str, Any]:
    """Đăng ký tài khoản mới (luôn tạo role 'user')."""
    return request(
        "POST",
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def get_me(token: str) -> dict[str, Any]:
    """Lấy thông tin user hiện tại từ token."""
    return request("GET", "/api/v1/auth/me", token=token)
