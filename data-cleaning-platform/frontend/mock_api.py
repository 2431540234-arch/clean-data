"""Backend giả (dữ liệu mẫu) cho frontend, bật bằng FRONTEND_MOCK=1.

Chỉ `api_client.request` được phép import module này. Mock mô phỏng đúng đường dẫn, tham số,
định dạng response và thông điệp lỗi của backend (theo backend/app/api/v1 và app/schemas).
Trạng thái lưu trong st.session_state nên mỗi phiên trình duyệt có dữ liệu riêng và được nạp
lại từ đầu khi tải lại trang.

Tài khoản mẫu:
    admin@example.com / Admin123!   (quản trị viên)
    user@example.com  / User12345   (người dùng thường)
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import streamlit as st

from api_client import APIError

DEMO_HINT = "Tài khoản dùng thử: admin@example.com / Admin123! · user@example.com / User12345"

_DB_KEY = "_mock_db"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Trạng thái
# ---------------------------------------------------------------------------


def _seed() -> dict[str, Any]:
    """Dữ liệu khởi tạo của một phiên mock."""
    created = "2026-09-01T08:00:00+00:00"
    users = [
        {
            "id": 1,
            "email": "admin@example.com",
            "password": "Admin123!",
            "full_name": "Trần Quốc Bảo",
            "role": "admin",
            "is_active": True,
            "created_at": created,
        },
        {
            "id": 2,
            "email": "user@example.com",
            "password": "User12345",
            "full_name": "Nguyễn Thị Minh Anh",
            "role": "user",
            "is_active": True,
            "created_at": created,
        },
    ]
    projects = [
        {
            "id": 1,
            "name": "Khách hàng 2026",
            "owner_id": 2,
            "created_at": "2026-09-12T03:20:00+00:00",
        },
        {
            "id": 2,
            "name": "Đơn hàng quý 3",
            "owner_id": 2,
            "created_at": "2026-10-05T07:45:00+00:00",
        },
        {
            "id": 3,
            "name": "Dữ liệu nội bộ",
            "owner_id": 1,
            "created_at": "2026-09-20T01:10:00+00:00",
        },
    ]
    return {"users": users, "next_user_id": 3, "projects": projects, "next_project_id": 4}


def db() -> dict[str, Any]:
    """Trạng thái mock của phiên hiện tại (tạo nếu chưa có)."""
    if _DB_KEY not in st.session_state:
        st.session_state[_DB_KEY] = _seed()
    return st.session_state[_DB_KEY]


# ---------------------------------------------------------------------------
# Khung định tuyến
# ---------------------------------------------------------------------------


@dataclass
class Call:
    """Một lời gọi API đã được giải mã, truyền vào handler."""

    method: str
    path: str
    token: str | None
    json: Any
    params: dict[str, Any]
    files: dict[str, Any] | None
    args: tuple[str, ...] = ()
    user: dict[str, Any] | None = field(default=None)


Handler = Callable[[Call], Any]
_ROUTES: list[tuple[str, re.Pattern[str], Handler, str]] = []


def route(method: str, pattern: str, *, access: str = "user") -> Callable[[Handler], Handler]:
    """Đăng ký handler. access: "public" | "user" (cần đăng nhập) | "admin"."""

    def decorator(func: Handler) -> Handler:
        _ROUTES.append((method, re.compile(f"^/api/v1{pattern}$"), func, access))
        return func

    return decorator


def _token_user(token: str | None) -> dict[str, Any]:
    """Giải mã token mock thành user (mô phỏng get_current_user của backend)."""
    if not token:
        raise APIError(401, "Thiếu token xác thực.")
    if not token.startswith("mock-token-"):
        raise APIError(401, "Token không hợp lệ hoặc đã hết hạn.")
    user_id = int(token.removeprefix("mock-token-"))
    user = next((u for u in db()["users"] if u["id"] == user_id), None)
    if user is None:
        raise APIError(401, "Người dùng không tồn tại.")
    if not user["is_active"]:
        raise APIError(401, "Tài khoản đã bị khóa.")
    return user


def handle(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: Any = None,
    params: dict[str, Any] | None = None,
    files: dict[str, Any] | None = None,
    raw: bool = False,
) -> Any:
    """Điểm vào duy nhất: thực thi một lời gọi API giả, trả dữ liệu hoặc raise APIError."""
    for route_method, pattern, handler, access in _ROUTES:
        match = pattern.match(path)
        if route_method != method or match is None:
            continue
        call = Call(method, path, token, json, params or {}, files, match.groups())
        if access != "public":
            call.user = _token_user(token)
            if access == "admin" and call.user["role"] != "admin":
                raise APIError(403, "Bạn không có quyền truy cập tài nguyên này.")
        return handler(call)
    raise APIError(404, "Không tìm thấy tài nguyên.")


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """UserOut: bỏ mật khẩu."""
    return {k: v for k, v in user.items() if k != "password"}


def validation_error(field_name: str, message: str) -> APIError:
    """Lỗi kiểm tra dữ liệu giống phản hồi 422 của FastAPI, đã rút gọn như api_client."""
    return APIError(422, f"{field_name}: {message}")


# ---------------------------------------------------------------------------
# Xác thực (auth)
# ---------------------------------------------------------------------------


def _token_for(user: dict[str, Any]) -> dict[str, str]:
    return {"access_token": f"mock-token-{user['id']}", "token_type": "bearer"}


@route("POST", "/auth/register", access="public")
def _register(call: Call) -> dict[str, str]:
    body = call.json or {}
    email = str(body.get("email", "")).strip()
    password = str(body.get("password", ""))
    full_name = str(body.get("full_name", "")).strip()
    if not _EMAIL_RE.match(email):
        raise validation_error("email", "Email không hợp lệ.")
    if len(password) < 8:
        raise validation_error("password", "Mật khẩu phải có ít nhất 8 ký tự.")
    if not full_name:
        raise validation_error("full_name", "Họ tên không được để trống.")
    state = db()
    if any(u["email"].lower() == email.lower() for u in state["users"]):
        raise APIError(409, "Email đã được sử dụng.")
    user = {
        "id": state["next_user_id"],
        "email": email,
        "password": password,
        "full_name": full_name,
        "role": "user",
        "is_active": True,
        "created_at": _now(),
    }
    state["next_user_id"] += 1
    state["users"].append(user)
    return _token_for(user)


@route("POST", "/auth/login", access="public")
def _login(call: Call) -> dict[str, str]:
    body = call.json or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    user = next((u for u in db()["users"] if u["email"].lower() == email), None)
    if user is None or user["password"] != password:
        raise APIError(401, "Email hoặc mật khẩu không đúng.")
    if not user["is_active"]:
        raise APIError(401, "Tài khoản đã bị khóa.")
    return _token_for(user)


@route("GET", "/auth/me")
def _me(call: Call) -> dict[str, Any]:
    assert call.user is not None
    return public_user(call.user)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def _get_project(project_id: int, user: dict[str, Any]) -> dict[str, Any]:
    """Lấy project và kiểm tra quyền (giống ensure_can_access_project)."""
    project = next((p for p in db()["projects"] if p["id"] == project_id), None)
    if project is None:
        raise APIError(404, "Không tìm thấy tài nguyên.")
    if user["role"] != "admin" and project["owner_id"] != user["id"]:
        raise APIError(403, "Bạn không có quyền truy cập tài nguyên này.")
    return project


def _project_name(body: Any) -> str:
    name = str((body or {}).get("name", "")).strip()
    if not name:
        raise validation_error("name", "Tên project không được để trống.")
    if len(name) > 255:
        raise validation_error("name", "Tên project tối đa 255 ký tự.")
    return name


@route("GET", "/projects")
def _list_projects(call: Call) -> list[dict[str, Any]]:
    assert call.user is not None
    projects = db()["projects"]
    if call.user["role"] == "admin":
        return list(projects)
    return [p for p in projects if p["owner_id"] == call.user["id"]]


@route("POST", "/projects")
def _create_project(call: Call) -> dict[str, Any]:
    assert call.user is not None
    state = db()
    project = {
        "id": state["next_project_id"],
        "name": _project_name(call.json),
        "owner_id": call.user["id"],
        "created_at": _now(),
    }
    state["next_project_id"] += 1
    state["projects"].append(project)
    return project


@route("GET", r"/projects/(\d+)")
def _read_project(call: Call) -> dict[str, Any]:
    assert call.user is not None
    return _get_project(int(call.args[0]), call.user)


@route("PUT", r"/projects/(\d+)")
def _update_project(call: Call) -> dict[str, Any]:
    assert call.user is not None
    project = _get_project(int(call.args[0]), call.user)
    project["name"] = _project_name(call.json)
    return project


@route("DELETE", r"/projects/(\d+)")
def _delete_project(call: Call) -> dict[str, str]:
    assert call.user is not None
    project = _get_project(int(call.args[0]), call.user)
    db()["projects"].remove(project)
    return {"message": "Đã xóa project."}
