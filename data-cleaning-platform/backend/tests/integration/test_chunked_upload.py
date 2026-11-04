"""Tải CSV lớn theo từng phần: mở phiên, gửi phần, hoàn tất; kết quả giống tải một lần."""

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.services import storage
from tests.conftest import FIXTURES_DIR

SAMPLE_DIR = FIXTURES_DIR.parent.parent.parent / "sample_data"
BASE = "/api/v1/datasets"


def _project(client, headers, name="Dự án thử"):
    return client.post("/api/v1/projects", json={"name": name}, headers=headers).json()["id"]


def _start(client, headers, project_id, filename, size):
    return client.post(
        f"{BASE}/uploads?project_id={project_id}",
        json={"filename": filename, "size": size},
        headers=headers,
    )


def _send(client, headers, upload_id, index, content):
    return client.put(
        f"{BASE}/uploads/{upload_id}/parts/{index}",
        files={"file": ("part", content, "application/octet-stream")},
        headers=headers,
    )


def _complete(client, headers, upload_id, parts):
    return client.post(
        f"{BASE}/uploads/{upload_id}/complete", json={"parts": parts}, headers=headers
    )


def _chunked(client, headers, project_id, filename, content, part_size, order=None):
    start = _start(client, headers, project_id, filename, len(content))
    assert start.status_code == 200, start.text
    upload_id = start.json()["upload_id"]
    parts = [content[i : i + part_size] for i in range(0, len(content), part_size)]
    for index in order if order is not None else range(len(parts)):
        assert _send(client, headers, upload_id, index, parts[index]).status_code == 200
    return upload_id, len(parts)


def _big_csv(rows=60_000) -> bytes:
    lines = ["id,ho_ten,email,so_dien_thoai"] + [
        f"{i},Nguyễn Văn {i % 97},user{i % 5000}@example.com,09{i % 100000000:08d}"
        for i in range(rows)
    ]
    return "\n".join(lines).encode("utf-8")


def test_start_returns_session_info(client, user_headers):
    response = _start(client, user_headers, _project(client, user_headers), "a.csv", 1000)
    body = response.json()
    assert response.status_code == 200
    assert len(body["upload_id"]) == 32
    assert body["part_size_bytes"] == settings.UPLOAD_PART_MB * 1024 * 1024
    assert body["max_bytes"] == settings.MAX_CHUNKED_UPLOAD_MB * 1024 * 1024


def test_chunked_upload_gives_the_same_dataset_as_a_single_upload(client, user_headers):
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()
    single = client.post(
        f"{BASE}/upload?project_id={project_id}",
        files={"file": ("khach_hang_ban.csv", content, "text/csv")},
        headers=user_headers,
    ).json()
    upload_id, parts = _chunked(
        client, user_headers, project_id, "khach_hang_ban.csv", content, 400
    )
    assert parts > 3
    response = _complete(client, user_headers, upload_id, parts)
    assert response.status_code == 200, response.text
    chunked = response.json()

    for key in ("row_count", "column_count"):
        assert chunked["first_version"][key] == single["first_version"][key]
    assert chunked["preview_rows"] == single["preview_rows"]
    assert chunked["dataset"]["encoding"] == single["dataset"]["encoding"]
    assert chunked["dataset"]["file_size"] == len(content) and chunked["sheet_names"] == []
    a = storage.load_dataframe_from_parquet(f"datasets/{single['dataset']['id']}/v1.parquet")
    b = storage.load_dataframe_from_parquet(f"datasets/{chunked['dataset']['id']}/v1.parquet")
    assert a.equals(b)
    assert storage.load_bytes(f"datasets/{chunked['dataset']['id']}/original.csv") == content


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


def test_parts_may_arrive_out_of_order_and_be_resent(client, user_headers):
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()
    size = 600
    count = -(-len(content) // size)
    upload_id, _ = _chunked(
        client, user_headers, project_id, "x.csv", content, size, order=list(reversed(range(count)))
    )
    assert _send(client, user_headers, upload_id, 0, content[:size]).status_code == 200  # gửi lại
    assert _complete(client, user_headers, upload_id, count).status_code == 200


def test_missing_part_is_reported_then_can_be_sent_and_completed(client, user_headers):
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()
    size = 600
    count = -(-len(content) // size)
    upload_id, _ = _chunked(
        client,
        user_headers,
        project_id,
        "x.csv",
        content,
        size,
        order=[i for i in range(count) if i != 1],
    )
    response = _complete(client, user_headers, upload_id, count)
    assert response.status_code == 422 and "thiếu 1 phần" in response.json()["detail"]
    assert _send(client, user_headers, upload_id, 1, content[size : 2 * size]).status_code == 200
    assert _complete(client, user_headers, upload_id, count).status_code == 200


def test_wrong_total_size_is_rejected(client, db, user_headers):
    project_id = _project(client, user_headers)
    content = b"a,b\n1,2\n3,4\n"
    upload_id = _start(client, user_headers, project_id, "x.csv", len(content) + 5).json()[
        "upload_id"
    ]
    _send(client, user_headers, upload_id, 0, content)
    response = _complete(client, user_headers, upload_id, 1)
    assert response.status_code == 422 and "không khớp" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []


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


def test_other_users_and_anonymous_cannot_touch_a_session(client, user_headers, other_headers):
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", 10).json()["upload_id"]
    assert _start(client, other_headers, project_id, "x.csv", 10).status_code == 403
    assert _send(client, other_headers, upload_id, 0, b"abc").status_code == 404
    assert _complete(client, other_headers, upload_id, 1).status_code == 404
    assert client.delete(f"{BASE}/uploads/{upload_id}", headers=other_headers).status_code == 404
    assert _start(client, {}, project_id, "x.csv", 10).status_code == 401
    assert _send(client, {}, upload_id, 0, b"abc").status_code == 401


def test_abort_removes_the_session(client, user_headers):
    project_id = _project(client, user_headers)
    upload_id = _start(client, user_headers, project_id, "x.csv", 10).json()["upload_id"]
    assert client.delete(f"{BASE}/uploads/{upload_id}", headers=user_headers).status_code == 204
    assert _send(client, user_headers, upload_id, 0, b"abc").status_code == 404


def test_broken_csv_fails_cleanly_and_leaves_nothing_behind(client, db, user_headers):
    project_id = _project(client, user_headers)
    content = b"id,ten\n"  # chỉ có dòng tiêu đề
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", content, 100)
    response = _complete(client, user_headers, upload_id, parts)
    assert response.status_code == 422 and "chỉ có dòng tiêu đề" in response.json()["detail"]
    assert db.scalars(select(Dataset)).all() == []
    assert _send(client, user_headers, upload_id, 0, content).status_code == 404  # phiên đã xóa


def test_completed_upload_writes_audit_log_and_clears_temp_files(client, db, user_headers):
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", content, 900)
    assert _complete(client, user_headers, upload_id, parts).status_code == 200
    log = db.scalars(select(AuditLog).where(AuditLog.action == "dataset.upload")).one()
    assert log.new_value["filename"] == "x.csv" and log.new_value["rows"] == 30
    assert _send(client, user_headers, upload_id, 0, b"abc").status_code == 404
    from pathlib import Path

    assert list(Path(settings.UPLOAD_TMP_DIR).iterdir()) == []


def test_storage_failure_during_chunked_upload_leaves_no_dataset(
    client, db, user_headers, monkeypatch
):
    def boom(*args, **kwargs):
        raise storage.StorageError("đĩa đầy")

    monkeypatch.setattr(storage, "save_file", boom)
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_ban.csv").read_bytes()
    upload_id, parts = _chunked(client, user_headers, project_id, "x.csv", content, 900)
    with TestClient(app, raise_server_exceptions=False) as lenient:
        response = _complete(lenient, user_headers, upload_id, parts)
    assert response.status_code == 500
    assert "đĩa đầy" not in response.text
    assert db.scalars(select(Dataset)).all() == []
