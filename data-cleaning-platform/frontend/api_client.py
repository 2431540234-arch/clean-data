"""Client gọi API backend bằng httpx, tự gắn JWT token (nếu có) vào header Authorization.

Đặt biến môi trường FRONTEND_MOCK=1 để chuyển sang dữ liệu mẫu (mock_api.py) thay vì gọi
backend thật. Đây là nơi DUY NHẤT chọn giữa mock và thật: các trang/component không biết.
"""

import os
from typing import Any

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
MOCK = os.environ.get("FRONTEND_MOCK", "").strip().lower() in {"1", "true", "yes"}

_SERVER_ERROR_MESSAGE = "Máy chủ gặp sự cố hoặc chức năng này chưa sẵn sàng. Vui lòng thử lại sau."
_CONNECTION_MESSAGE = "Không kết nối được tới máy chủ. Vui lòng kiểm tra mạng và thử lại."
_TIMEOUT_MESSAGE = "Máy chủ phản hồi quá lâu. Vui lòng thử lại sau ít phút."


class APIError(Exception):
    """Lỗi khi gọi API backend, giữ lại status_code và thông báo lỗi để hiển thị cho người dùng.

    `detail` là thông điệp tiếng Việt thân thiện cho người dùng; `technical` giữ nội dung gốc
    (nếu có) để hiển thị trong phần "Chi tiết kỹ thuật".
    """

    def __init__(self, status_code: int, detail: str, technical: str | None = None) -> None:
        self.status_code = status_code
        self.detail = detail
        self.technical = technical
        super().__init__(detail)


class APIConnectionError(APIError):
    """Không kết nối được hoặc quá thời gian chờ (status_code = 0)."""

    def __init__(self, detail: str, technical: str | None = None) -> None:
        super().__init__(0, detail, technical)


def data_source_label() -> str | None:
    """Nhãn nguồn dữ liệu để giao diện hiển thị khi không dùng backend thật, None nếu là thật."""
    return "Chế độ dữ liệu mẫu" if MOCK else None


def _headers(token: str | None) -> dict[str, str]:
    """Dựng header Authorization nếu có token."""
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _format_detail(body: Any) -> str | None:
    """Rút gọn trường `detail` của backend (chuỗi, hoặc danh sách lỗi Pydantic) thành một câu."""
    if not isinstance(body, dict):
        return None
    detail = body.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                field = ".".join(str(p) for p in item.get("loc", []) if p not in ("body", "query"))
                msg = str(item.get("msg", ""))
                parts.append(f"{field}: {msg}" if field else msg)
        return "; ".join(p for p in parts if p) or None
    return None


def _raise_for_response(response: httpx.Response) -> None:
    """Chuyển response lỗi (>= 400) thành APIError với thông điệp thân thiện."""
    try:
        body = response.json()
    except ValueError:
        body = None
    detail = _format_detail(body)
    technical = response.text[:500] or None

    if response.status_code >= 500 or detail is None:
        # Lỗi 5xx của backend (kể cả NotImplementedError) trả text thô: không đưa cho người dùng.
        message = (
            _SERVER_ERROR_MESSAGE
            if response.status_code >= 500
            else (f"Yêu cầu không thành công (mã {response.status_code}).")
        )
        raise APIError(response.status_code, message, technical)
    raise APIError(response.status_code, detail, technical)


def request(
    method: str,
    path: str,
    token: str | None = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    timeout: float = 30.0,
    raw: bool = False,
) -> Any:
    """Gọi API backend tại BACKEND_URL + path, raise APIError nếu không thành công.

    Args:
        method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE".
        path: đường dẫn API, ví dụ "/api/v1/auth/login".
        token: JWT access token, nếu có sẽ gắn vào header Authorization.
        json: body JSON (dict hoặc list).
        raw: True để nhận nguyên bytes của response (dùng cho tải file xuất).

    Raises:
        APIError: backend trả lỗi (status >= 400).
        APIConnectionError: không kết nối được hoặc quá thời gian chờ.
    """
    if MOCK:
        import mock_api

        return mock_api.handle(
            method, path, token=token, json=json, params=params, files=files, raw=raw
        )

    url = f"{BACKEND_URL}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method, url, headers=_headers(token), json=json, params=params, files=files
            )
    except httpx.TimeoutException as exc:
        raise APIConnectionError(_TIMEOUT_MESSAGE, repr(exc)) from exc
    except httpx.TransportError as exc:
        raise APIConnectionError(_CONNECTION_MESSAGE, repr(exc)) from exc

    if response.status_code >= 400:
        _raise_for_response(response)

    if raw:
        return response.content
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
