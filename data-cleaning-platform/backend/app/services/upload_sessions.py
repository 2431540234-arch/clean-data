"""Phiên tải file lên theo từng phần (chunked upload), chỉ dùng cho CSV lớn.

Frontend chia file thành các phần nhỏ (UPLOAD_PART_MB) rồi gửi lần lượt; server giữ các phần trong
thư mục tạm, khi đủ thì ghép lại thành MỘT file duy nhất rồi mới đọc và làm sạch như file thường.
Nhờ vậy kết quả làm sạch giống hệt xử lý cả file, chỉ khác là không phải gửi file lớn trong một yêu
cầu. Phiên chỉ nằm trên đĩa (không có bảng DB) và tự dọn sau UPLOAD_SESSION_TTL_MINUTES phút.
"""

import json
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import NotFoundError, PayloadTooLargeError, ValidationAppError

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_META = "meta.json"
_MAX_PARTS = 5000


@dataclass
class UploadSession:
    """Thông tin một phiên tải lên đang mở."""

    upload_id: str
    user_id: int
    project_id: int
    filename: str
    size: int
    directory: Path


def max_bytes() -> int:
    return settings.MAX_CHUNKED_UPLOAD_MB * 1024 * 1024


def part_bytes() -> int:
    return settings.UPLOAD_PART_MB * 1024 * 1024


def _root() -> Path:
    root = Path(settings.UPLOAD_TMP_DIR)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root  # tương đối so với thư mục backend/
    return root


def purge_expired() -> int:
    """Xóa các phiên quá hạn (kể cả phiên bị bỏ dở); trả số phiên đã xóa."""
    root = _root()
    if not root.is_dir():
        return 0
    deadline = time.time() - settings.UPLOAD_SESSION_TTL_MINUTES * 60
    removed = 0
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        newest = max((p.stat().st_mtime for p in entry.rglob("*") if p.is_file()), default=0)
        newest = max(newest, entry.stat().st_mtime)
        if newest < deadline:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def create(user_id: int, project_id: int, filename: str, size: int) -> UploadSession:
    """Mở một phiên mới; từ chối file rỗng hoặc vượt trần MAX_CHUNKED_UPLOAD_MB."""
    if size <= 0:
        raise ValidationAppError("File không có dữ liệu.")
    if size > max_bytes():
        raise PayloadTooLargeError(f"File vượt quá {settings.MAX_CHUNKED_UPLOAD_MB} MB.")
    purge_expired()
    upload_id = uuid.uuid4().hex
    directory = _root() / upload_id
    directory.mkdir(parents=True, exist_ok=False)
    meta = {"user_id": user_id, "project_id": project_id, "filename": filename, "size": size}
    (directory / _META).write_text(json.dumps(meta), encoding="utf-8")
    return UploadSession(upload_id, user_id, project_id, filename, size, directory)


def get(upload_id: str, user_id: int) -> UploadSession:
    """Lấy phiên của đúng người dùng; phiên của người khác hoặc đã hết hạn coi như không tồn tại."""
    directory = _root() / upload_id
    if not _ID_RE.match(upload_id) or not (directory / _META).is_file():
        raise NotFoundError("Không tìm thấy phiên tải lên (có thể đã hết hạn).")
    meta = json.loads((directory / _META).read_text(encoding="utf-8"))
    if meta["user_id"] != user_id:
        raise NotFoundError("Không tìm thấy phiên tải lên (có thể đã hết hạn).")
    return UploadSession(
        upload_id, meta["user_id"], meta["project_id"], meta["filename"], meta["size"], directory
    )


def _part_path(session: UploadSession, index: int) -> Path:
    return session.directory / f"{index:05d}.part"


def received_bytes(session: UploadSession) -> int:
    return sum(p.stat().st_size for p in session.directory.glob("*.part"))


def save_part(session: UploadSession, index: int, content: bytes) -> int:
    """Lưu phần thứ `index` (đánh số từ 0, gửi lại cùng số thì ghi đè); trả tổng byte đã nhận."""
    if not 0 <= index < _MAX_PARTS:
        raise ValidationAppError("Số thứ tự phần không hợp lệ.")
    if not content:
        raise ValidationAppError("Phần tải lên rỗng.")
    if len(content) > part_bytes():
        raise PayloadTooLargeError(f"Mỗi phần tối đa {settings.UPLOAD_PART_MB} MB.")
    target = _part_path(session, index)
    previous = target.stat().st_size if target.is_file() else 0
    total = received_bytes(session) - previous + len(content)
    if total > session.size:
        raise ValidationAppError("Tổng dung lượng các phần vượt quá dung lượng đã khai báo.")
    temp = target.with_suffix(".tmp")
    temp.write_bytes(content)
    temp.replace(target)
    return total


def assemble(session: UploadSession, part_count: int) -> Path:
    """Ghép các phần 0..part_count-1 thành một file; kiểm tra đủ phần và đủ dung lượng khai báo."""
    if not 1 <= part_count <= _MAX_PARTS:
        raise ValidationAppError("Số phần không hợp lệ.")
    missing = [i for i in range(part_count) if not _part_path(session, i).is_file()]
    if missing:
        shown = ", ".join(str(i) for i in missing[:10])
        raise ValidationAppError(f"Còn thiếu {len(missing)} phần (số thứ tự: {shown}).")
    target = session.directory / "assembled"
    with target.open("wb") as out:
        for index in range(part_count):
            with _part_path(session, index).open("rb") as part:
                shutil.copyfileobj(part, out, length=1024 * 1024)
    size = target.stat().st_size
    if size != session.size:
        target.unlink()
        raise ValidationAppError(
            f"Dung lượng sau khi ghép ({size} byte) không khớp dung lượng đã khai báo "
            f"({session.size} byte); hãy tải lại."
        )
    return target


def discard(session: UploadSession) -> None:
    """Xóa phiên và mọi phần của nó."""
    shutil.rmtree(session.directory, ignore_errors=True)
