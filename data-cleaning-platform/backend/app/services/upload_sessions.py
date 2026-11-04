"""Phiên tải file lên theo từng phần (chunked upload), chỉ dùng cho CSV lớn.

Frontend chia file thành các phần nhỏ (UPLOAD_PART_MB) rồi gửi lần lượt; server giữ các phần trong
thư mục tạm, khi đủ thì ghép lại thành MỘT file duy nhất rồi mới đọc và làm sạch như file thường.
Nhờ vậy kết quả làm sạch giống hệt xử lý cả file, chỉ khác là không phải gửi file lớn trong một yêu
cầu. Phiên chỉ nằm trên đĩa (không có bảng DB) và tự dọn sau UPLOAD_SESSION_TTL_MINUTES phút.

Toàn vẹn: server không tin frontend. Tổng dung lượng, kích thước từng phần và mã SHA-256 (nếu client
gửi) đều được server kiểm lại; mã SHA-256 của cả file bắt được cả trường hợp các phần bị đổi chỗ cho
nhau (cùng kích thước nên không thể phát hiện chỉ bằng dung lượng).

Dọn dẹp (không có tác vụ định kỳ): khi khởi động ứng dụng, khi mở phiên mới, tối đa mỗi phút một lần
khi nhận phần, và khi chính phiên đó được truy cập sau khi đã hết hạn.
"""

import hashlib
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
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_META = "meta.json"
_MAX_PARTS = 5000
_PURGE_INTERVAL_SECONDS = 60
_last_purge = 0.0


@dataclass
class UploadSession:
    """Thông tin một phiên tải lên đang mở."""

    upload_id: str
    user_id: int
    project_id: int
    filename: str
    size: int
    part_size: int  # kích thước mỗi phần đã chốt lúc mở phiên (mọi phần trừ phần cuối phải đúng cỡ)
    sha256: str | None  # mã SHA-256 của cả file do client khai báo (nếu có)
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


def _last_activity(directory: Path) -> float:
    newest = directory.stat().st_mtime
    for path in directory.rglob("*"):
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return newest


def _is_expired(directory: Path) -> bool:
    return _last_activity(directory) < time.time() - settings.UPLOAD_SESSION_TTL_MINUTES * 60


def purge_expired() -> int:
    """Xóa các phiên quá hạn (kể cả phiên bị bỏ dở); trả số phiên đã xóa."""
    root = _root()
    if not root.is_dir():
        return 0
    removed = 0
    for entry in root.iterdir():
        if entry.is_dir() and _is_expired(entry):
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def _purge_if_due() -> None:
    """Dọn phiên quá hạn nhưng tối đa mỗi phút một lần (gọi được ở đường nóng như nhận phần)."""
    global _last_purge
    now = time.time()
    if now - _last_purge >= _PURGE_INTERVAL_SECONDS:
        _last_purge = now
        purge_expired()


def _check_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    if not _SHA256_RE.match(value):
        raise ValidationAppError("Mã SHA-256 không hợp lệ (cần 64 ký tự thập lục phân).")
    return value.lower()


def create(
    user_id: int, project_id: int, filename: str, size: int, sha256: str | None = None
) -> UploadSession:
    """Mở một phiên mới; từ chối file rỗng hoặc vượt trần MAX_CHUNKED_UPLOAD_MB."""
    global _last_purge
    if size <= 0:
        raise ValidationAppError("File không có dữ liệu.")
    if size > max_bytes():
        raise PayloadTooLargeError(f"File vượt quá {settings.MAX_CHUNKED_UPLOAD_MB} MB.")
    sha256 = _check_sha256(sha256)
    _last_purge = time.time()
    purge_expired()
    upload_id = uuid.uuid4().hex
    directory = _root() / upload_id
    directory.mkdir(parents=True, exist_ok=False)
    meta = {
        "user_id": user_id,
        "project_id": project_id,
        "filename": filename,
        "size": size,
        "part_size": part_bytes(),
        "sha256": sha256,
    }
    (directory / _META).write_text(json.dumps(meta), encoding="utf-8")
    return UploadSession(
        upload_id, user_id, project_id, filename, size, meta["part_size"], sha256, directory
    )


def get(upload_id: str, user_id: int) -> UploadSession:
    """Lấy phiên của đúng người dùng; phiên của người khác, hết hạn hoặc đã xóa coi như không có."""
    missing = NotFoundError("Không tìm thấy phiên tải lên (có thể đã hết hạn).")
    directory = _root() / upload_id
    if not _ID_RE.match(upload_id) or not (directory / _META).is_file():
        raise missing
    meta = json.loads((directory / _META).read_text(encoding="utf-8"))
    if meta["user_id"] != user_id:
        raise missing
    if _is_expired(directory):
        shutil.rmtree(
            directory, ignore_errors=True
        )  # quá hạn: xóa luôn, không chờ lượt dọn kế tiếp
        raise missing
    return UploadSession(
        upload_id,
        meta["user_id"],
        meta["project_id"],
        meta["filename"],
        meta["size"],
        meta["part_size"],
        meta.get("sha256"),
        directory,
    )


def _part_path(session: UploadSession, index: int) -> Path:
    return session.directory / f"{index:05d}.part"


def received_bytes(session: UploadSession) -> int:
    return sum(p.stat().st_size for p in session.directory.glob("*.part"))


def save_part(session: UploadSession, index: int, content: bytes, sha256: str | None = None) -> int:
    """Lưu phần thứ `index` (đánh số từ 0, gửi lại cùng số thì ghi đè); trả tổng byte đã nhận.

    Nếu client gửi `sha256` của phần này thì server tính lại và từ chối khi không khớp.
    """
    _purge_if_due()
    if not 0 <= index < _MAX_PARTS:
        raise ValidationAppError("Số thứ tự phần không hợp lệ.")
    if not content:
        raise ValidationAppError("Phần tải lên rỗng.")
    if len(content) > session.part_size:
        raise PayloadTooLargeError(f"Mỗi phần tối đa {session.part_size // (1024 * 1024)} MB.")
    expected = _check_sha256(sha256)
    if expected is not None and hashlib.sha256(content).hexdigest() != expected:
        raise ValidationAppError(
            f"Phần {index} bị hỏng khi truyền (mã SHA-256 không khớp); hãy gửi lại phần này."
        )
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
    """Ghép các phần 0..part_count-1 thành một file sau khi kiểm tra kỹ.

    Kiểm tra theo thứ tự: đủ phần; mọi phần trừ phần cuối đúng kích thước đã chốt; tổng dung
    lượng bằng dung lượng khai báo; mã SHA-256 của cả file (nếu có). Lỗi thì không để lại file
    ghép dở; các phần đã gửi vẫn được giữ để client gửi bù hoặc gửi lại phần sai.
    """
    if not 1 <= part_count <= _MAX_PARTS:
        raise ValidationAppError("Số phần không hợp lệ.")
    missing = [i for i in range(part_count) if not _part_path(session, i).is_file()]
    if missing:
        shown = ", ".join(str(i) for i in missing[:10])
        raise ValidationAppError(f"Còn thiếu {len(missing)} phần (số thứ tự: {shown}).")
    for index in range(part_count - 1):  # phần cuối được phép ngắn hơn
        size = _part_path(session, index).stat().st_size
        if size != session.part_size:
            raise ValidationAppError(
                f"Phần {index} có {size} byte, cần đúng {session.part_size} byte "
                "(mọi phần trừ phần cuối phải đủ kích thước); hãy gửi lại phần này."
            )
    target = session.directory / "assembled"
    digest = hashlib.sha256()
    with target.open("wb") as out:
        for index in range(part_count):
            with _part_path(session, index).open("rb") as part:
                while block := part.read(1024 * 1024):
                    out.write(block)
                    digest.update(block)
    size = target.stat().st_size
    if size != session.size:
        target.unlink()
        raise ValidationAppError(
            f"Dung lượng sau khi ghép ({size} byte) không khớp dung lượng đã khai báo "
            f"({session.size} byte); hãy tải lại."
        )
    if session.sha256 is not None and digest.hexdigest() != session.sha256:
        target.unlink()
        raise ValidationAppError(
            "Nội dung sau khi ghép không khớp mã SHA-256 của file gốc "
            "(các phần có thể bị đổi thứ tự hoặc hỏng); hãy tải lại."
        )
    return target


def discard(session: UploadSession) -> None:
    """Xóa phiên và mọi phần của nó."""
    shutil.rmtree(session.directory, ignore_errors=True)
