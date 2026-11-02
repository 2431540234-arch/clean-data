"""Backend giả (dữ liệu mẫu) cho frontend, bật bằng FRONTEND_MOCK=1.

Chỉ `api_client.request` được phép import module này. Mock mô phỏng đúng đường dẫn, tham số,
định dạng response và thông điệp lỗi của backend (theo backend/app/api/v1 và app/schemas).
Trạng thái lưu trong st.session_state nên mỗi phiên trình duyệt có dữ liệu riêng và được nạp
lại từ đầu khi tải lại trang.

Tài khoản mẫu:
    admin@example.com / Admin123!   (quản trị viên)
    user@example.com  / User12345   (người dùng thường)
"""

import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import streamlit as st

import mock_data
import mock_mapping
import mock_profiling
import mock_rules
import mock_suggest
from api_client import _SERVER_ERROR_MESSAGE, APIError
from components.labels import op_label

DEMO_HINT = "Tài khoản dùng thử: admin@example.com / Admin123! · user@example.com / User12345"

# FRONTEND_MOCK_FAIL=suggestions,preview,versions: các nhóm API này luôn trả lỗi máy chủ (để thử
# giao diện ở trạng thái lỗi). Chỉ có tác dụng ở chế độ mock.
_FAIL_PREFIXES = tuple(
    prefix.strip()
    for prefix in os.environ.get("FRONTEND_MOCK_FAIL", "").split(",")
    if prefix.strip()
)

_DB_KEY = "_mock_db"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Trạng thái
# ---------------------------------------------------------------------------


def _add_dataset(
    state: dict[str, Any],
    *,
    project_id: int,
    user_id: int,
    filename: str,
    file_type: str,
    file_size: int,
    encoding: str | None,
    sheet_name: str | None,
    frame: Any,
    created_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Tạo dataset + version đầu tiên trong trạng thái mock. Trả (dataset, version)."""
    dataset_id, version_id = state["next_dataset_id"], state["next_version_id"]
    state["next_dataset_id"] += 1
    state["next_version_id"] += 1
    dataset = {
        "id": dataset_id,
        "project_id": project_id,
        "name": filename.rsplit(".", 1)[0],
        "original_filename": filename,
        "file_type": file_type,
        "file_size": file_size,
        "encoding": encoding,
        "sheet_name": sheet_name,
        "current_version_id": version_id,
        "uploaded_by": user_id,
        "created_at": created_at,
        "updated_at": created_at,
    }
    version = {
        "id": version_id,
        "dataset_id": dataset_id,
        "version_number": 1,
        "row_count": len(frame),
        "column_count": len(frame.columns),
        "parent_version_id": None,
        "change_summary": "Tải lên ban đầu",
        "created_by": user_id,
        "created_at": created_at,
    }
    state["datasets"].append(dataset)
    state["versions"].append(version)
    state["frames"][version_id] = frame
    return dataset, version


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
    state: dict[str, Any] = {
        "users": users,
        "next_user_id": 3,
        "projects": projects,
        "next_project_id": 4,
        "datasets": [],
        "versions": [],
        "frames": {},  # version_id -> DataFrame
        "raw_files": {},  # dataset_id -> (bytes, loại file), để chọn lại sheet
        "profiles": {},  # version_id -> list[SchemaProfileOut]
        "quality": {},  # version_id -> QualityReportOut
        "suggestions": [],  # SuggestionOut
        "next_dataset_id": 1,
        "next_version_id": 1,
        "next_id": 1,  # id chung cho profile/quality/...
    }
    _add_dataset(
        state,
        project_id=1,
        user_id=2,
        filename=mock_data.SAMPLE_FILENAME,
        file_type="csv",
        file_size=len(mock_data.SAMPLE_CSV.encode()),
        encoding="utf-8",
        sheet_name=None,
        frame=mock_data.sample_frame(),
        created_at="2026-09-12T04:00:00+00:00",
    )
    return state


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
    if any(path.startswith(f"/api/v1/{prefix}") for prefix in _FAIL_PREFIXES):
        raise APIError(500, _SERVER_ERROR_MESSAGE, "Mock: lỗi giả lập bởi FRONTEND_MOCK_FAIL")
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


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

_UPLOAD_TYPES = {"csv": "csv", "tsv": "csv", "txt": "csv", "xlsx": "xlsx", "xls": "xlsx"}


def _get_dataset(dataset_id: int, user: dict[str, Any]) -> dict[str, Any]:
    """Lấy dataset và kiểm tra quyền qua project của nó."""
    dataset = next((d for d in db()["datasets"] if d["id"] == dataset_id), None)
    if dataset is None:
        raise APIError(404, "Không tìm thấy tài nguyên.")
    _get_project(dataset["project_id"], user)
    return dataset


def _first_version(dataset: dict[str, Any]) -> dict[str, Any]:
    return next(
        v for v in db()["versions"] if v["dataset_id"] == dataset["id"] and v["version_number"] == 1
    )


def _upload_response(dataset: dict[str, Any], sheet_names: list[str]) -> dict[str, Any]:
    first = _first_version(dataset)
    return {
        "dataset": dataset,
        "first_version": first,
        "sheet_names": sheet_names,
        "preview_rows": mock_data.preview_rows(db()["frames"][first["id"]]),
    }


@route("POST", "/datasets/upload")
def _upload_dataset(call: Call) -> dict[str, Any]:
    assert call.user is not None
    try:
        project_id = int(call.params.get("project_id"))
    except (TypeError, ValueError):
        raise validation_error("project_id", "Thiếu project_id.") from None
    _get_project(project_id, call.user)
    if not call.files or "file" not in call.files:
        raise validation_error("file", "Chưa chọn file.")
    filename, content = call.files["file"][0], call.files["file"][1]
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    file_type = _UPLOAD_TYPES.get(extension)
    if file_type is None:
        raise APIError(422, "Định dạng file không được hỗ trợ. Chỉ nhận CSV hoặc Excel.")
    if len(content) > mock_data.MAX_UPLOAD_MB * 1024 * 1024:
        raise APIError(422, f"File vượt quá {mock_data.MAX_UPLOAD_MB} MB.")
    try:
        if file_type == "csv":
            frame, encoding = mock_data.read_csv_bytes(content)
            sheet_names: list[str] = []
            sheet = None
        else:
            sheet_names = mock_data.excel_sheet_names(content)
            sheet = sheet_names[0]
            frame, encoding = mock_data.read_excel_bytes(content, sheet), None
    except mock_data.UploadProblem as exc:
        raise APIError(422, str(exc)) from exc
    except Exception as exc:
        raise APIError(
            422, "Không đọc được nội dung file. File có thể bị hỏng hoặc sai định dạng."
        ) from exc
    if frame.empty or len(frame.columns) == 0:
        raise APIError(422, "File không có dữ liệu.")

    state = db()
    dataset, _ = _add_dataset(
        state,
        project_id=project_id,
        user_id=call.user["id"],
        filename=filename,
        file_type=file_type,
        file_size=len(content),
        encoding=encoding,
        sheet_name=sheet,
        frame=frame,
        created_at=_now(),
    )
    state["raw_files"][dataset["id"]] = (content, file_type)
    return _upload_response(dataset, sheet_names)


@route("GET", r"/datasets/(\d+)")
def _read_dataset(call: Call) -> dict[str, Any]:
    assert call.user is not None
    return _get_dataset(int(call.args[0]), call.user)


@route("GET", r"/datasets/(\d+)/versions")
def _list_dataset_versions(call: Call) -> list[dict[str, Any]]:
    assert call.user is not None
    dataset = _get_dataset(int(call.args[0]), call.user)
    return [v for v in db()["versions"] if v["dataset_id"] == dataset["id"]]


@route("POST", r"/datasets/(\d+)/select-sheet")
def _select_sheet(call: Call) -> dict[str, Any]:
    assert call.user is not None
    state = db()
    dataset = _get_dataset(int(call.args[0]), call.user)
    raw = state["raw_files"].get(dataset["id"])
    if raw is None or raw[1] != "xlsx":
        raise APIError(422, "Dataset này không phải file Excel.")
    sheet_names = mock_data.excel_sheet_names(raw[0])
    sheet = call.params.get("sheet_name")
    if sheet not in sheet_names:
        raise APIError(422, "Sheet không tồn tại trong file.")
    frame = mock_data.read_excel_bytes(raw[0], sheet)
    if frame.empty:
        raise APIError(422, "Sheet này không có dữ liệu.")
    first = _first_version(dataset)
    state["frames"][first["id"]] = frame
    first.update(row_count=len(frame), column_count=len(frame.columns))
    dataset.update(sheet_name=sheet, current_version_id=first["id"], updated_at=_now())
    return _upload_response(dataset, sheet_names)


# ---------------------------------------------------------------------------
# Profiling và chất lượng
# ---------------------------------------------------------------------------


def _get_version(version_id: int, user: dict[str, Any]) -> dict[str, Any]:
    """Lấy version và kiểm tra quyền qua dataset -> project."""
    version = next((v for v in db()["versions"] if v["id"] == version_id), None)
    if version is None:
        raise APIError(404, "Không tìm thấy tài nguyên.")
    _get_dataset(version["dataset_id"], user)
    return version


def _next_id(count: int = 1) -> int:
    state = db()
    first = state["next_id"]
    state["next_id"] += count
    return first


@route("POST", r"/profiling/(\d+)/run")
def _run_profiling(call: Call) -> dict[str, Any]:
    assert call.user is not None
    version = _get_version(int(call.args[0]), call.user)
    frame = db()["frames"][version["id"]]
    columns = mock_profiling.profile_frame(
        frame, version["id"], _next_id(len(frame.columns)), _now()
    )
    db()["profiles"][version["id"]] = columns
    return {"version_id": version["id"], "columns": columns}


@route("GET", r"/profiling/(\d+)")
def _get_profiling(call: Call) -> dict[str, Any]:
    assert call.user is not None
    version = _get_version(int(call.args[0]), call.user)
    columns = db()["profiles"].get(version["id"])
    if columns is None:
        raise APIError(404, "Chưa có kết quả profiling cho phiên bản này.")
    return {"version_id": version["id"], "columns": columns}


@route("GET", r"/quality/(\d+)")
def _get_quality(call: Call) -> dict[str, Any]:
    assert call.user is not None
    state = db()
    version = _get_version(int(call.args[0]), call.user)
    if version["id"] not in state["quality"]:
        frame = state["frames"][version["id"]]
        state["quality"][version["id"]] = mock_profiling.quality_report(
            frame, version["id"], _next_id(), _now()
        )
    return state["quality"][version["id"]]


# ---------------------------------------------------------------------------
# Mapping cột
# ---------------------------------------------------------------------------


@route("POST", r"/mapping/(\d+)/suggest")
def _suggest_mapping(call: Call) -> dict[str, str | None]:
    assert call.user is not None
    version = _get_version(int(call.args[0]), call.user)
    targets = call.json
    if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
        raise validation_error("body", "Cần một danh sách tên cột chuẩn.")
    if not targets:
        raise validation_error("body", "Danh sách cột chuẩn không được rỗng.")
    columns = [str(c) for c in db()["frames"][version["id"]].columns]
    return mock_mapping.suggest_mapping(columns, targets)


# ---------------------------------------------------------------------------
# Gợi ý, xem trước, áp dụng rule
# ---------------------------------------------------------------------------


@route("POST", "/suggestions/generate")
def _generate_suggestions(call: Call) -> list[dict[str, Any]]:
    assert call.user is not None
    state = db()
    version_id = (call.json or {}).get("version_id")
    if not isinstance(version_id, int):
        raise validation_error("version_id", "Thiếu version_id.")
    version = _get_version(version_id, call.user)
    state["suggestions"] = [s for s in state["suggestions"] if s["version_id"] != version["id"]]
    now = _now()
    created = []
    for draft in mock_suggest.generate(state["frames"][version["id"]]):
        item = {
            "id": _next_id(),
            "version_id": version["id"],
            **draft,
            "status": "pending",
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": now,
        }
        state["suggestions"].append(item)
        created.append(item)
    return created


@route("GET", r"/suggestions/by-version/(\d+)")
def _list_suggestions(call: Call) -> list[dict[str, Any]]:
    assert call.user is not None
    version = _get_version(int(call.args[0]), call.user)
    return [s for s in db()["suggestions"] if s["version_id"] == version["id"]]


@route("POST", r"/suggestions/(\d+)/decision")
def _decide_suggestion(call: Call) -> dict[str, Any]:
    assert call.user is not None
    item = next((s for s in db()["suggestions"] if s["id"] == int(call.args[0])), None)
    if item is None:
        raise APIError(404, "Không tìm thấy tài nguyên.")
    _get_version(item["version_id"], call.user)
    decision = (call.json or {}).get("decision")
    if decision not in {"accepted", "rejected"}:
        raise validation_error("decision", "Quyết định phải là accepted hoặc rejected.")
    item.update(status=decision, reviewed_by=call.user["id"], reviewed_at=_now())
    return item


@route("POST", "/preview")
def _preview(call: Call) -> dict[str, Any]:
    assert call.user is not None
    body = call.json or {}
    version = _get_version(int(body.get("version_id", 0)), call.user)
    try:
        steps = mock_rules.validate_steps((body.get("rule_set") or {}).get("steps"))
        sample_rows = max(1, min(int(body.get("sample_rows", 50)), 500))
        result = mock_rules.compute_preview(db()["frames"][version["id"]], steps, sample_rows)
    except mock_rules.RuleError as exc:
        raise APIError(422, str(exc)) from exc
    return {"version_id": version["id"], **result}


def _summarize(steps: list[dict[str, Any]]) -> str:
    """Mô tả thay đổi của một đợt áp dụng bằng nhãn tiếng Việt (mock tự đặt, backend tự quyết)."""
    parts = [
        f"{op_label(s['op'])} ({s['column']})" if s.get("column") else op_label(s["op"])
        for s in steps
    ]
    return f"Áp dụng {len(steps)} bước: " + "; ".join(parts)


@route("POST", r"/versions/(\d+)/apply")
def _apply_rule_set(call: Call) -> dict[str, Any]:
    assert call.user is not None
    state = db()
    dataset = _get_dataset(int(call.args[0]), call.user)
    try:
        steps = mock_rules.validate_steps((call.json or {}).get("steps"))
        if not steps:
            raise mock_rules.RuleError("Không có bước nào để áp dụng.")
        parent_id = dataset["current_version_id"]
        frame, _, _ = mock_rules.apply_steps(state["frames"][parent_id], steps)
    except mock_rules.RuleError as exc:
        raise APIError(422, str(exc)) from exc
    versions = [v for v in state["versions"] if v["dataset_id"] == dataset["id"]]
    version = {
        "id": state["next_version_id"],
        "dataset_id": dataset["id"],
        "version_number": max(v["version_number"] for v in versions) + 1,
        "row_count": len(frame),
        "column_count": len(frame.columns),
        "parent_version_id": parent_id,
        "change_summary": _summarize(steps),
        "created_by": call.user["id"],
        "created_at": _now(),
    }
    state["next_version_id"] += 1
    state["versions"].append(version)
    state["frames"][version["id"]] = frame
    dataset.update(current_version_id=version["id"], updated_at=_now())
    return version


# ---------------------------------------------------------------------------
# Undo / redo / khôi phục phiên bản
# ---------------------------------------------------------------------------


def _switch_version(dataset: dict[str, Any], version_id: int) -> dict[str, Any]:
    """Đặt phiên bản hiện tại của dataset (không xóa phiên bản nào)."""
    version = next(v for v in db()["versions"] if v["id"] == version_id)
    dataset.update(current_version_id=version_id, updated_at=_now())
    return version


def _current_version(dataset: dict[str, Any]) -> dict[str, Any]:
    return next(v for v in db()["versions"] if v["id"] == dataset["current_version_id"])


@route("POST", r"/versions/(\d+)/undo")
def _undo(call: Call) -> dict[str, Any]:
    assert call.user is not None
    dataset = _get_dataset(int(call.args[0]), call.user)
    parent_id = _current_version(dataset)["parent_version_id"]
    if parent_id is None:
        raise APIError(422, "Không còn phiên bản trước để hoàn tác.")
    return _switch_version(dataset, parent_id)


@route("POST", r"/versions/(\d+)/redo")
def _redo(call: Call) -> dict[str, Any]:
    assert call.user is not None
    dataset = _get_dataset(int(call.args[0]), call.user)
    children = [
        v for v in db()["versions"] if v["parent_version_id"] == dataset["current_version_id"]
    ]
    if not children:
        raise APIError(422, "Không có phiên bản nào để làm lại.")
    return _switch_version(dataset, max(children, key=lambda v: v["version_number"])["id"])


@route("POST", r"/versions/(\d+)/restore/(\d+)")
def _restore(call: Call) -> dict[str, Any]:
    assert call.user is not None
    dataset = _get_dataset(int(call.args[0]), call.user)
    version_id = int(call.args[1])
    if not any(
        v["id"] == version_id and v["dataset_id"] == dataset["id"] for v in db()["versions"]
    ):
        raise APIError(404, "Không tìm thấy tài nguyên.")
    return _switch_version(dataset, version_id)
