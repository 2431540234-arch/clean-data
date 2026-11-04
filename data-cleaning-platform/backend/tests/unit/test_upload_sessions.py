"""Phiên tải lên theo từng phần: tạo, nhận phần, ghép, hết hạn."""

import os
import time

import pytest

from app.core.config import settings
from app.core.exceptions import NotFoundError, PayloadTooLargeError, ValidationAppError
from app.services import upload_sessions as sessions


def _session(size=10, user_id=1):
    return sessions.create(user_id, 7, "file.csv", size)


def test_parts_can_arrive_in_any_order_and_are_assembled_in_order():
    session = _session(size=9)
    sessions.save_part(session, 2, b"ghi")
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 3).read_bytes() == b"abcdefghi"


def test_resending_a_part_overwrites_it_without_double_counting():
    session = _session(size=6)
    sessions.save_part(session, 0, b"xxx")
    assert sessions.save_part(session, 0, b"abc") == 3
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 2).read_bytes() == b"abcdef"


def test_missing_parts_are_reported_and_session_is_kept_for_resending():
    session = _session(size=9)
    sessions.save_part(session, 0, b"abc")
    sessions.save_part(session, 2, b"ghi")
    with pytest.raises(ValidationAppError, match="thiếu 1 phần.*1"):
        sessions.assemble(session, 3)
    sessions.save_part(session, 1, b"def")
    assert sessions.assemble(session, 3).read_bytes() == b"abcdefghi"


def test_size_mismatch_after_assembling_is_rejected():
    session = _session(size=10)
    sessions.save_part(session, 0, b"abc")
    with pytest.raises(ValidationAppError, match="không khớp"):
        sessions.assemble(session, 1)
    assert not (session.directory / "assembled").exists()


def test_total_of_parts_cannot_exceed_declared_size():
    session = _session(size=5)
    sessions.save_part(session, 0, b"abc")
    with pytest.raises(ValidationAppError, match="vượt quá"):
        sessions.save_part(session, 1, b"defg")


@pytest.mark.parametrize("index", [-1, 5000, 99999])
def test_part_index_must_be_in_range(index):
    with pytest.raises(ValidationAppError, match="Số thứ tự"):
        sessions.save_part(_session(), index, b"a")


def test_empty_and_oversized_parts_are_rejected(monkeypatch):
    session = _session(size=10 * 1024 * 1024)
    with pytest.raises(ValidationAppError, match="rỗng"):
        sessions.save_part(session, 0, b"")
    monkeypatch.setattr(settings, "UPLOAD_PART_MB", 1)
    with pytest.raises(PayloadTooLargeError):
        sessions.save_part(session, 0, b"x" * (1024 * 1024 + 1))


def test_create_rejects_empty_and_too_large_files(monkeypatch):
    with pytest.raises(ValidationAppError):
        sessions.create(1, 7, "f.csv", 0)
    monkeypatch.setattr(settings, "MAX_CHUNKED_UPLOAD_MB", 1)
    with pytest.raises(PayloadTooLargeError, match="1 MB"):
        sessions.create(1, 7, "f.csv", 1024 * 1024 + 1)
    assert sessions.create(1, 7, "f.csv", 1024 * 1024).size == 1024 * 1024


def test_session_belongs_to_one_user_and_bad_ids_look_like_missing():
    session = _session(user_id=1)
    assert sessions.get(session.upload_id, 1).filename == "file.csv"
    for bad in (session.upload_id, "../" + session.upload_id, "x" * 32, ""):
        with pytest.raises(NotFoundError):
            sessions.get(bad, 2) if bad == session.upload_id else sessions.get(bad, 1)


def test_discard_removes_everything():
    session = _session()
    sessions.save_part(session, 0, b"a")
    sessions.discard(session)
    assert not session.directory.exists()
    with pytest.raises(NotFoundError):
        sessions.get(session.upload_id, 1)


def test_expired_sessions_are_purged_but_fresh_ones_are_kept(monkeypatch):
    old, fresh = _session(), _session()
    for path in [old.directory, *old.directory.iterdir()]:
        os.utime(path, (time.time() - 3 * 3600, time.time() - 3 * 3600))
    assert sessions.purge_expired() == 1
    assert not old.directory.exists() and fresh.directory.exists()
    monkeypatch.setattr(settings, "UPLOAD_SESSION_TTL_MINUTES", 0)
    time.sleep(0.05)
    assert sessions.purge_expired() == 1
    assert not fresh.directory.exists()
