"""Tải CSV lớn theo từng phần: mở phiên, gửi phần, hoàn tất; kết quả giống tải một lần."""

import hashlib
import os
import time
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.services import storage, upload_sessions
from tests.conftest import FIXTURES_DIR

SAMPLE_DIR = FIXTURES_DIR.parent.parent.parent / "sample_data"
BASE = "/api/v1/datasets"
SAMPLE = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _small_parts(monkeypatch, size: int) -> None:
    """Phần nhỏ để test gọn; server chốt cỡ này lúc mở phiên và đòi mọi phần (trừ cuối) đúng cỡ."""
    monkeypatch.setattr(upload_sessions, "part_bytes", lambda: size)


def _project(client, headers, name="Dự án thử"):
    return client.post("/api/v1/projects", json={"name": name}, headers=headers).json()["id"]


def _start(client, headers, project_id, filename, size, sha256=None):
    body = {"filename": filename, "size": size}
    if sha256 is not None:
        body["sha256"] = sha256
    return client.post(f"{BASE}/uploads?project_id={project_id}", json=body, headers=headers)


def _send(client, headers, upload_id, index, content, sha256=None):
    return client.put(
        f"{BASE}/uploads/{upload_id}/parts/{index}",
        params={"sha256": sha256} if sha256 is not None else None,
        files={"file": ("part", content, "application/octet-stream")},
        headers=headers,
    )


def _send_ok(client, headers, upload_id, index, content):
    return _send(client, headers, upload_id, index, content, _sha(content))


def _complete(client, headers, upload_id, parts):
    return client.post(
        f"{BASE}/uploads/{upload_id}/complete", json={"parts": parts}, headers=headers
    )


def _chunked(client, headers, project_id, filename, content, part_size, order=None, checksums=True):
    """Làm như frontend: khai báo dung lượng (+ SHA-256), cắt phần đúng cỡ rồi gửi."""
    sha = _sha(content) if checksums else None
    start = _start(client, headers, project_id, filename, len(content), sha)
    assert start.status_code == 200, start.text
    upload_id = start.json()["upload_id"]
    parts = [content[i : i + part_size] for i in range(0, len(content), part_size)]
    for index in order if order is not None else range(len(parts)):
        part_sha = _sha(parts[index]) if checksums else None
        assert _send(client, headers, upload_id, index, parts[index], part_sha).status_code == 200
    return upload_id, len(parts)


def _age(path: Path, hours: float) -> None:
    moment = time.time() - hours * 3600
    for item in [path, *path.rglob("*")]:
        os.utime(item, (moment, moment))


def _session_dirs() -> list[Path]:
    root = Path(settings.UPLOAD_TMP_DIR)
    return list(root.iterdir()) if root.is_dir() else []


def _big_csv(rows=60_000) -> bytes:
    lines = ["id,ho_ten,email,so_dien_thoai"] + [
        f"{i},Nguyễn Văn {i % 97},user{i % 5000}@example.com,09{i % 100000000:08d}"
        for i in range(rows)
    ]
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------- luồng chính


def test_start_returns_session_info(client, user_headers):
    response = _start(client, user_headers, _project(client, user_headers), "a.csv", 1000)
    body = response.json()
    assert response.status_code == 200
    assert len(body["upload_id"]) == 32
    assert body["part_size_bytes"] == settings.UPLOAD_PART_MB * 1024 * 1024
    assert body["max_bytes"] == settings.MAX_CHUNKED_UPLOAD_MB * 1024 * 1024


def test_chunked_upload_gives_the_same_dataset_as_a_single_upload(
    client, user_headers, monkeypatch
):
    _small_parts(monkeypatch, 400)
    project_id = _project(client, user_headers)
    single = client.post(
        f"{BASE}/upload?project_id={project_id}",
        files={"file": ("khach_hang_ban.csv", SAMPLE, "text/csv")},
        headers=user_headers,
    ).json()
    upload_id, parts = _chunked(client, user_headers, project_id, "khach_hang_ban.csv", SAMPLE, 400)
    assert parts > 3
    response = _complete(client, user_headers, upload_id, parts)
    assert response.status_code == 200, response.text
    chunked = response.json()

    for key in ("row_count", "column_count"):
        assert chunked["first_version"][key] == single["first_version"][key]
    assert chunked["preview_rows"] == single["preview_rows"]
    assert chunked["dataset"]["encoding"] == single["dataset"]["encoding"]
    assert chunked["dataset"]["file_size"] == len(SAMPLE) and chunked["sheet_names"] == []
    a = storage.load_dataframe_from_parquet(f"datasets/{single['dataset']['id']}/v1.parquet")
    b = storage.load_dataframe_from_parquet(f"datasets/{chunked['dataset']['id']}/v1.parquet")
    assert a.equals(b)
    assert storage.load_bytes(f"datasets/{chunked['dataset']['id']}/original.csv") == SAMPLE


def test_file_over_the_single_upload_limit_works_in_parts_and_exports_completely(
    client, user_headers, monkeypatch
):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)  # tải một lần chỉ nhận tới 1 MB
    monkeypatch.setattr(settings, "UPLOAD_PART_MB", 1)
    project_id = _project(client, user_headers)
    content = _big_csv()
    assert len(content) > 2 * 1024 * 1024

    single = client.post(
        f"{BASE}/upload?project_id={project_id}",
        files={"file": ("lon.csv", content, "text/csv")},
        headers=user_headers,
    )
    assert single.status_code == 413  # đúng hành vi cũ

    upload_id, parts = _chunked(client, user_headers, project_id, "lon.csv", content, 1024 * 1024)
    assert parts >= 3
    response = _complete(client, user_headers, upload_id, parts)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_version"]["row_count"] == 60_000
    version_id, dataset_id = body["first_version"]["id"], body["dataset"]["id"]

    rows = client.get(
        f"{BASE}/{dataset_id}/versions/{version_id}/rows?offset=59990&limit=100",
        headers=user_headers,
    ).json()
    assert rows["total"] == 60_000 and rows["rows"][-1]["values"]["id"] == "59999"

    # xử lý và xuất cả bộ như file thường: xuất ra một file CSV đủ 60.000 dòng
    exported = client.get(f"/api/v1/export/{version_id}/csv", headers=user_headers)
    assert exported.status_code == 200
    frame = pd.read_csv(pd.io.common.BytesIO(exported.content), encoding="utf-8-sig", dtype=str)
    assert len(frame) == 60_000 and list(frame.columns) == [
        "id",
        "ho_ten",
        "email",
        "so_dien_thoai",
    ]
    assert client.get(f"/api/v1/quality/{version_id}", headers=user_headers).status_code == 200


# ---------------------------------------------------------------- toàn vẹn khi gửi phần


def test_parts_may_arrive_out_of_order(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    count = -(-len(SAMPLE) // 600)
    upload_id, _ = _chunked(
        client, user_headers, project_id, "x.csv", SAMPLE, 600, order=list(reversed(range(count)))
    )
    response = _complete(client, user_headers, upload_id, count)
    assert response.status_code == 200
    original = storage.load_bytes(f"datasets/{response.json()['dataset']['id']}/original.csv")
    assert original == SAMPLE  # ghép đúng thứ tự dù gửi ngược


def test_resending_the_same_part_twice_does_not_duplicate_data(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    count = -(-len(SAMPLE) // 600)
    upload_id, _ = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    for index in (0, 0, count - 1, 1, 1):  # gửi lại đủ kiểu, kể cả phần đầu và phần cuối
        part = SAMPLE[index * 600 : (index + 1) * 600]
        assert _send_ok(client, user_headers, upload_id, index, part).status_code == 200
    response = _complete(client, user_headers, upload_id, count)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["first_version"]["row_count"] == 30  # không bị nhân đôi dòng
    assert body["dataset"]["file_size"] == len(SAMPLE)
    original = storage.load_bytes(f"datasets/{body['dataset']['id']}/original.csv")
    assert original == SAMPLE and original.count(b"\n") == SAMPLE.count(b"\n")


def test_missing_part_is_reported_then_can_be_sent_and_completed(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    count = -(-len(SAMPLE) // 600)
    upload_id, _ = _chunked(
        client,
        user_headers,
        project_id,
        "x.csv",
        SAMPLE,
        600,
        order=[i for i in range(count) if i != 1],
    )
    response = _complete(client, user_headers, upload_id, count)
    assert response.status_code == 422
    assert "thiếu 1 phần (số thứ tự: 1)" in response.json()["detail"]
    assert _send_ok(client, user_headers, upload_id, 1, SAMPLE[600:1200]).status_code == 200
    assert _complete(client, user_headers, upload_id, count).status_code == 200


def test_claiming_more_parts_than_sent_is_rejected(client, db, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    count = -(-len(SAMPLE) // 600)
    upload_id, _ = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    response = _complete(client, user_headers, upload_id, count + 2)
    assert response.status_code == 422 and "thiếu 2 phần" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []


def test_part_with_the_wrong_size_is_rejected_at_complete(client, db, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", 1100).json()["upload_id"]
    _send(client, user_headers, upload_id, 0, b"a" * 500)  # phần giữa thiếu 100 byte
    _send(client, user_headers, upload_id, 1, b"a" * 600)
    response = _complete(client, user_headers, upload_id, 2)
    assert response.status_code == 422
    assert "Phần 0 có 500 byte, cần đúng 600 byte" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []


def test_part_larger_than_the_session_part_size_is_refused(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 100)
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", 1000).json()["upload_id"]
    assert _send(client, user_headers, upload_id, 0, b"x" * 101).status_code == 413


def test_server_checks_total_size_and_does_not_trust_the_declaration(
    client, db, user_headers, monkeypatch
):
    _small_parts(monkeypatch, 100)
    project_id = _project(client, user_headers)
    # khai báo nhỏ hơn thực tế: phần vượt tổng khai báo bị từ chối ngay
    upload_id = _start(client, user_headers, project_id, "x.csv", 150).json()["upload_id"]
    assert _send(client, user_headers, upload_id, 0, b"a" * 100).status_code == 200
    too_much = _send(client, user_headers, upload_id, 1, b"a" * 100)
    assert too_much.status_code == 422 and "vượt quá" in too_much.json()["detail"]
    # khai báo lớn hơn thực tế: hoàn tất bị từ chối vì dung lượng không khớp
    upload_id = _start(client, user_headers, project_id, "y.csv", 500).json()["upload_id"]
    _send(client, user_headers, upload_id, 0, b"a,b\n1,2\n")
    response = _complete(client, user_headers, upload_id, 1)
    assert response.status_code == 422 and "không khớp" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []
    # trần do server giữ, không do client
    too_big = settings.MAX_CHUNKED_UPLOAD_MB * 1024 * 1024 + 1
    assert _start(client, user_headers, project_id, "z.csv", too_big).status_code == 413


def test_corrupted_part_is_rejected_by_its_checksum_and_not_stored(
    client, user_headers, monkeypatch
):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", len(SAMPLE)).json()["upload_id"]
    response = _send(client, user_headers, upload_id, 0, SAMPLE[:600], _sha(b"khac"))
    assert response.status_code == 422 and "Phần 0 bị hỏng khi truyền" in response.json()["detail"]
    assert _send(client, user_headers, upload_id, 0, SAMPLE[:600], "xyz").status_code == 422
    assert not list(_session_dirs()[0].glob("*.part"))


def test_swapped_parts_are_caught_by_the_file_checksum_then_fixed_by_resending(
    client, db, user_headers, monkeypatch
):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    started = _start(client, user_headers, project_id, "x.csv", len(SAMPLE), _sha(SAMPLE))
    upload_id = started.json()["upload_id"]
    count = -(-len(SAMPLE) // 600)
    parts = [SAMPLE[i * 600 : (i + 1) * 600] for i in range(count)]
    parts[0], parts[1] = parts[1], parts[0]  # đổi chỗ hai phần cùng kích thước
    for index, content in enumerate(parts):
        assert _send_ok(client, user_headers, upload_id, index, content).status_code == 200
    response = _complete(client, user_headers, upload_id, count)
    assert response.status_code == 422 and "SHA-256" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []  # không tạo dataset từ dữ liệu sai chỗ
    for index in (0, 1):  # gửi lại đúng thì hoàn tất được trên cùng phiên
        _send_ok(client, user_headers, upload_id, index, SAMPLE[index * 600 : (index + 1) * 600])
    assert _complete(client, user_headers, upload_id, count).status_code == 200


def test_malformed_file_checksum_is_rejected_when_opening_the_session(client, user_headers):
    project_id = _project(client, user_headers)
    response = _start(client, user_headers, project_id, "x.csv", 10, "khong-phai-sha256")
    assert response.status_code == 422


def test_limits_are_enforced_at_start_and_for_each_part(client, user_headers, monkeypatch):
    project_id = _project(client, user_headers)
    monkeypatch.setattr(settings, "MAX_CHUNKED_UPLOAD_MB", 1)
    assert _start(client, user_headers, project_id, "x.csv", 1024 * 1024 + 1).status_code == 413
    monkeypatch.setattr(settings, "UPLOAD_PART_MB", 1)
    upload_id = _start(client, user_headers, project_id, "x.csv", 1024 * 1024).json()["upload_id"]
    too_big = _send(client, user_headers, upload_id, 0, b"x" * (1024 * 1024 + 1))
    assert too_big.status_code == 413


def test_only_csv_is_accepted_for_chunked_upload(client, user_headers):
    project_id = _project(client, user_headers)
    for name in ("a.xlsx", "a.xls", "a.txt"):
        assert _start(client, user_headers, project_id, name, 100).status_code == 422


# ---------------------------------------------------------------- quyền


def test_other_users_cannot_send_complete_or_abort_and_the_owner_is_unaffected(
    client, user_headers, other_headers, monkeypatch
):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    upload_id, count = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    assert _start(client, other_headers, project_id, "x.csv", 10).status_code == 403
    assert _send(client, other_headers, upload_id, 0, b"abc").status_code == 404
    assert _complete(client, other_headers, upload_id, count).status_code == 404
    assert client.delete(f"{BASE}/uploads/{upload_id}", headers=other_headers).status_code == 404
    assert _start(client, {}, project_id, "x.csv", 10).status_code == 401
    assert _send(client, {}, upload_id, 0, b"abc").status_code == 401
    assert _complete(client, {}, upload_id, count).status_code == 401
    assert client.delete(f"{BASE}/uploads/{upload_id}").status_code == 401
    # phiên của chủ vẫn nguyên vẹn sau mọi nỗ lực trên
    assert _complete(client, user_headers, upload_id, count).status_code == 200


def test_admin_can_open_sessions_in_any_project_but_not_use_other_peoples(
    client, user_headers, admin_headers
):
    project_id = _project(client, user_headers)
    assert _start(client, admin_headers, project_id, "x.csv", 10).status_code == 200
    upload_id = _start(client, user_headers, project_id, "y.csv", 10).json()["upload_id"]
    assert _send(client, admin_headers, upload_id, 0, b"abc").status_code == 404  # phiên của user


# ---------------------------------------------------------------- audit log


def test_completed_upload_writes_one_audit_log(client, db, user_headers, monkeypatch):
    _small_parts(monkeypatch, 900)
    project_id = _project(client, user_headers)
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 900)
    assert _complete(client, user_headers, upload_id, parts).status_code == 200
    log = db.scalars(select(AuditLog).where(AuditLog.action == "dataset.upload")).one()
    assert log.new_value["filename"] == "x.csv" and log.new_value["rows"] == 30


def test_opening_and_aborting_a_session_write_no_audit_log(client, db, user_headers):
    """Ghi lại hiện trạng: chỉ lần hoàn tất (đã tạo dữ liệu) mới có nhật ký."""
    project_id = _project(client, user_headers)
    before = [a.action for a in db.scalars(select(AuditLog)).all()]
    upload_id = _start(client, user_headers, project_id, "x.csv", 10).json()["upload_id"]
    client.delete(f"{BASE}/uploads/{upload_id}", headers=user_headers)
    assert [a.action for a in db.scalars(select(AuditLog)).all()] == before


# ---------------------------------------------------------------- dọn dẹp và hết hạn


def test_abort_removes_the_session_and_its_parts(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    upload_id, _ = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    assert len(_session_dirs()) == 1
    assert client.delete(f"{BASE}/uploads/{upload_id}", headers=user_headers).status_code == 204
    assert _session_dirs() == []  # không còn thư mục hay phần nào
    assert _send(client, user_headers, upload_id, 0, b"abc").status_code == 404


def test_completed_upload_leaves_no_temp_files(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    assert _complete(client, user_headers, upload_id, parts).status_code == 200
    assert _session_dirs() == []  # phần, file ghép và Parquet tạm đều đã xóa
    assert _send(client, user_headers, upload_id, 0, b"abc").status_code == 404


def test_broken_csv_fails_cleanly_and_leaves_nothing_behind(client, db, user_headers):
    project_id = _project(client, user_headers)
    content = b"id,ten\n"  # chỉ có dòng tiêu đề
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", content, 100)
    response = _complete(client, user_headers, upload_id, parts)
    assert response.status_code == 422 and "chỉ có dòng tiêu đề" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []
    assert _session_dirs() == []
    assert _send(client, user_headers, upload_id, 0, content).status_code == 404


def test_storage_failure_leaves_no_dataset_and_no_temp_files(client, db, user_headers, monkeypatch):
    def boom(*args, **kwargs):
        raise storage.StorageError("đĩa đầy")

    monkeypatch.setattr(storage, "save_file", boom)
    _small_parts(monkeypatch, 900)
    project_id = _project(client, user_headers)
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 900)
    with TestClient(app, raise_server_exceptions=False) as lenient:
        response = _complete(lenient, user_headers, upload_id, parts)
    assert response.status_code == 500
    assert "đĩa đầy" not in response.text
    assert db.scalars(select(Dataset)).all() == []
    assert _session_dirs() == []


def test_expired_session_is_refused_and_its_files_are_deleted(client, user_headers, monkeypatch):
    _small_parts(monkeypatch, 600)
    project_id = _project(client, user_headers)
    count = -(-len(SAMPLE) // 600)
    upload_id, _ = _chunked(client, user_headers, project_id, "x.csv", SAMPLE, 600)
    _age(_session_dirs()[0], hours=2)  # quá UPLOAD_SESSION_TTL_MINUTES (60 phút)
    assert _send(client, user_headers, upload_id, 0, SAMPLE[:600]).status_code == 404
    assert _session_dirs() == []  # bị xóa ngay khi bị chạm tới
    assert _complete(client, user_headers, upload_id, count).status_code == 404


def test_abandoned_sessions_are_purged_when_someone_opens_a_new_one(client, user_headers):
    project_id = _project(client, user_headers)
    abandoned = _start(client, user_headers, project_id, "x.csv", 10).json()["upload_id"]
    _age(_session_dirs()[0], hours=3)
    fresh = _start(client, user_headers, project_id, "y.csv", 10).json()["upload_id"]
    assert [p.name for p in _session_dirs()] == [fresh] and abandoned != fresh


def test_session_ttl_is_configurable(client, user_headers, monkeypatch):
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", 10).json()["upload_id"]
    _age(_session_dirs()[0], hours=2)
    monkeypatch.setattr(settings, "UPLOAD_SESSION_TTL_MINUTES", 24 * 60)  # nới lên một ngày
    assert _send(client, user_headers, upload_id, 0, b"abc").status_code == 200
