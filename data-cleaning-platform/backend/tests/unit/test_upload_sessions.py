"""Phiên tải lên theo từng phần: tạo, nhận phần, kiểm tra toàn vẹn, ghép, hết hạn."""

import hashlib
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import NotFoundError, PayloadTooLargeError, ValidationAppError
from app.main import app
from app.services import upload_sessions as sessions


@pytest.fixture(autouse=True)
def tiny_parts(monkeypatch):
    """Mỗi phần 3 byte để test gọn: mọi phần trừ phần cuối phải đúng 3 byte."""
    monkeypatch.setattr(sessions, "part_bytes", lambda: 3)


def _session(size=9, user_id=1, sha256=None):
    return sessions.create(user_id, 7, "file.csv", size, sha256)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _age(directory: Path, hours: float) -> None:
    """Làm như phiên không có hoạt động từ `hours` giờ trước."""
    moment = time.time() - hours * 3600
    for path in [directory, *directory.rglob("*")]:
        os.utime(path, (moment, moment))


# ---------------------------------------------------------------- ghép phần


def test_parts_can_arrive_in_any_order_and_are_assembled_in_order():
    session = _session()
    sessions.save_part(session, 2, b"ghi")
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 3).read_bytes() == b"abcdefghi"


def test_the_last_part_may_be_shorter():
    session = _session(size=7)
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 1, b"def")
    sessions.save_part(session, 2, b"g")
    assert sessions.assemble(session, 3).read_bytes() == b"abcdefg"


def test_resending_a_part_overwrites_it_without_double_counting():
    session = _session(size=6)
    sessions.save_part(session, 0, b"xxx")
    assert sessions.save_part(session, 0, b"abc") == 3  # không cộng dồn hai lần
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 2).read_bytes() == b"abcdef"  # không bị ghép trùng


def test_missing_parts_are_reported_and_session_is_kept_for_resending():
    session = _session()
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 2, b"ghi")
    with pytest.raises(ValidationAppError, match="thiếu 1 phần.*1"):
        sessions.assemble(session, 3)
    assert not (session.directory / "assembled").exists()
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 3).read_bytes() == b"abcdefghi"


def test_claiming_more_parts_than_were_sent_is_a_missing_part_error():
    session = _session(size=6)
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 1, b"def")
    with pytest.raises(ValidationAppError, match="thiếu 1 phần"):
        sessions.assemble(session, 3)


def test_a_middle_part_with_the_wrong_size_is_rejected_with_its_index():
    session = _session(size=5)
    sessions.save_part(session, 0, b"ab")  # ngắn hơn 3 byte nhưng không phải phần cuối
    sessions.save_part(session, 1, b"cde")
    with pytest.raises(ValidationAppError, match="Phần 0 có 2 byte, cần đúng 3 byte"):
        sessions.assemble(session, 2)
    assert not (session.directory / "assembled").exists()  # không để lại file ghép dở


# ---------------------------------------------------------------- tổng dung lượng do server kiểm


def test_size_mismatch_after_assembling_is_rejected():
    session = _session(size=10)
    sessions.save_part(session, 0, b"abc")
    with pytest.raises(ValidationAppError, match="không khớp"):
        sessions.assemble(session, 1)
    assert not (session.directory / "assembled").exists()


def test_client_cannot_send_more_than_it_declared():
    session = _session(size=5)
    sessions.save_part(session, 0, b"abc")
    with pytest.raises(ValidationAppError, match="vượt quá"):
        sessions.save_part(session, 1, b"def")  # 3 + 3 > 5


def test_declared_size_is_capped_by_the_server_not_the_client(monkeypatch):
    with pytest.raises(ValidationAppError):
        sessions.create(1, 7, "f.csv", 0)
    monkeypatch.setattr(settings, "MAX_CHUNKED_UPLOAD_MB", 1)
    with pytest.raises(PayloadTooLargeError, match="1 MB"):
        sessions.create(1, 7, "f.csv", 1024 * 1024 + 1)
    assert sessions.create(1, 7, "f.csv", 1024 * 1024).size == 1024 * 1024


def test_part_size_is_fixed_when_the_session_opens(monkeypatch):
    session = _session()
    monkeypatch.setattr(sessions, "part_bytes", lambda: 100)  # đổi cấu hình giữa chừng
    assert sessions.get(session.upload_id, 1).part_size == 3
    with pytest.raises(PayloadTooLargeError):
        sessions.save_part(session, 0, b"abcd")


@pytest.mark.parametrize("index", [-1, 5000, 99999])
def test_part_index_must_be_in_range(index):
    with pytest.raises(ValidationAppError, match="Số thứ tự"):
        sessions.save_part(_session(), index, b"a")


def test_empty_and_oversized_parts_are_rejected():
    session = _session()
    with pytest.raises(ValidationAppError, match="rỗng"):
        sessions.save_part(session, 0, b"")
    with pytest.raises(PayloadTooLargeError, match="tối đa"):
        sessions.save_part(session, 0, b"abcd")


# ---------------------------------------------------------------- mã kiểm tra SHA-256


def test_part_checksum_is_verified_by_the_server():
    session = _session()
    assert sessions.save_part(session, 0, b"abc", _sha(b"abc")) == 3
    assert sessions.save_part(session, 1, b"def", _sha(b"def").upper()) == 6  # hoa thường đều được
    with pytest.raises(ValidationAppError, match="Phần 2 bị hỏng khi truyền"):
        sessions.save_part(session, 2, b"ghi", _sha(b"khac"))
    assert not (session.directory / "00002.part").exists()  # phần hỏng không được lưu


@pytest.mark.parametrize("bad", ["", "abc", "z" * 64, "a" * 63])
def test_malformed_checksums_are_rejected(bad):
    with pytest.raises(ValidationAppError, match="SHA-256 không hợp lệ"):
        _session(sha256=bad)
    with pytest.raises(ValidationAppError, match="SHA-256 không hợp lệ"):
        sessions.save_part(_session(), 0, b"abc", bad)


def test_file_checksum_catches_parts_swapped_with_the_same_size():
    whole = b"abcdefghi"
    session = _session(sha256=_sha(whole))
    sessions.save_part(session, 0, b"def")  # sai chỗ: phần 0 và 1 bị đổi cho nhau
    sessions.save_part(session, 1, b"abc")
    sessions.save_part(session, 2, b"ghi")
    with pytest.raises(ValidationAppError, match="đổi thứ tự hoặc hỏng"):
        sessions.assemble(session, 3)
    assert not (session.directory / "assembled").exists()
    sessions.save_part(session, 0, b"abc")  # gửi lại đúng thì ghép được
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 3).read_bytes() == whole


def test_without_a_file_checksum_swapped_equal_size_parts_cannot_be_detected():
    """Ghi lại giới hạn có chủ đích: chỉ dung lượng thì không thấy được việc đổi chỗ hai phần."""
    session = _session()
    sessions.save_part(session, 0, b"def")
    sessions.save_part(session, 1, b"abc")
    sessions.save_part(session, 2, b"ghi")
    assert sessions.assemble(session, 3).read_bytes() == b"defabcghi"


# ---------------------------------------------------------------- quyền, hết hạn, dọn dẹp


def test_session_belongs_to_one_user_and_bad_ids_look_like_missing():
    session = _session(user_id=1)
    assert sessions.get(session.upload_id, 1).filename == "file.csv"
    with pytest.raises(NotFoundError):
        sessions.get(session.upload_id, 2)
    for bad in ("../" + session.upload_id, "x" * 32, ""):
        with pytest.raises(NotFoundError):
            sessions.get(bad, 1)


def test_discard_removes_everything():
    session = _session()
    sessions.save_part(session, 0, b"a")
    sessions.discard(session)
    assert not session.directory.exists()
    with pytest.raises(NotFoundError):
        sessions.get(session.upload_id, 1)


def test_an_expired_session_is_refused_and_deleted_when_touched():
    session = _session()
    sessions.save_part(session, 0, b"abc")
    _age(session.directory, hours=2)  # TTL mặc định 60 phút
    with pytest.raises(NotFoundError):
        sessions.get(session.upload_id, 1)
    assert not session.directory.exists()


def test_activity_keeps_a_session_alive():
    session = _session()
    _age(session.directory, hours=0.9)  # 54 phút: chưa hết hạn
    assert sessions.get(session.upload_id, 1).upload_id == session.upload_id
    sessions.save_part(session, 0, b"abc")  # có hoạt động mới thì tính lại từ đầu
    _age(session.directory / "00000.part", hours=0)
    assert sessions.get(session.upload_id, 1)


def test_expired_sessions_are_purged_but_fresh_ones_are_kept(monkeypatch):
    old, fresh = _session(), _session()
    _age(old.directory, hours=3)
    assert sessions.purge_expired() == 1
    assert not old.directory.exists() and fresh.directory.exists()
    monkeypatch.setattr(settings, "UPLOAD_SESSION_TTL_MINUTES", 0)
    time.sleep(0.05)
    assert sessions.purge_expired() == 1
    assert not fresh.directory.exists()


def test_opening_a_new_session_purges_expired_ones():
    old = _session()
    _age(old.directory, hours=3)
    new = _session()
    assert not old.directory.exists() and new.directory.exists()


def test_receiving_parts_purges_expired_sessions_at_most_once_per_interval(monkeypatch):
    abandoned, active = _session(), _session()
    _age(abandoned.directory, hours=3)
    monkeypatch.setattr(sessions, "_last_purge", time.time())  # vừa dọn xong: chưa đến lượt
    sessions.save_part(active, 0, b"abc")
    assert abandoned.directory.exists()
    monkeypatch.setattr(sessions, "_last_purge", time.time() - 120)  # đã quá một phút
    sessions.save_part(active, 1, b"def")
    assert not abandoned.directory.exists() and active.directory.exists()


def test_expired_sessions_left_by_a_previous_run_are_purged_at_startup():
    leftover = _session()
    sessions.save_part(leftover, 0, b"abc")
    _age(leftover.directory, hours=5)
    with TestClient(app):  # vào lifespan = khởi động ứng dụng
        assert not leftover.directory.exists()


def test_startup_survives_a_purge_failure(monkeypatch):
    def boom():
        raise OSError("đĩa lỗi")

    monkeypatch.setattr(sessions, "purge_expired", boom)
    with TestClient(app) as client:  # không được chặn ứng dụng khởi động
        assert client.get("/health").status_code == 200
