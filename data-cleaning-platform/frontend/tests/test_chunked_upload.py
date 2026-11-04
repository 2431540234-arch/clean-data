"""Tải CSV lớn theo từng phần: quy tắc giới hạn, mock API và hàm tự tách phần của api_client."""

import hashlib

import pytest

import api_client
import mock_data
from components.upload_rules import (
    CHUNK_THRESHOLD_MB,
    MAX_CSV_MB,
    MAX_EXCEL_MB,
    size_problem,
    use_parts,
)

MB = 1024 * 1024


def _csv(rows: int) -> bytes:
    lines = ["id,ho_ten,email"] + [f"{i},Nguyễn Văn {i},u{i}@example.com" for i in range(rows)]
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------- quy tắc thuần


@pytest.mark.parametrize(
    ("name", "size", "expected"),
    [
        ("a.csv", 1 * MB, False),
        ("a.csv", CHUNK_THRESHOLD_MB * MB, False),
        ("a.csv", CHUNK_THRESHOLD_MB * MB + 1, True),
        ("A.CSV", 150 * MB, True),
        ("a.xlsx", 49 * MB, False),
        ("a.xlsx", MAX_EXCEL_MB * MB, False),  # Excel luôn tải một lần
    ],
)
def test_only_big_csv_is_uploaded_in_parts(name, size, expected):
    assert use_parts(name, size) is expected


def test_csv_limit_is_200_mb_and_excel_limit_is_50_mb_with_a_hint():
    assert size_problem("a.csv", MAX_CSV_MB * MB) is None
    assert "200 MB" in size_problem("a.csv", MAX_CSV_MB * MB + 1)
    assert size_problem("a.xlsx", MAX_EXCEL_MB * MB) is None
    message = size_problem("a.xlsx", MAX_EXCEL_MB * MB + 1)
    assert "50 MB" in message and "CSV" in message and "200 MB" in message


def test_frontend_limits_match_the_mock_and_the_backend_defaults():
    assert mock_data.MAX_CHUNKED_UPLOAD_MB == MAX_CSV_MB == 200
    assert mock_data.MAX_UPLOAD_MB == MAX_EXCEL_MB == 50


# ---------------------------------------------------------------- mock API và tự tách phần


def test_upload_in_parts_gives_the_same_dataset_as_a_single_upload(call_api, monkeypatch):
    monkeypatch.setattr(mock_data, "UPLOAD_PART_MB", 1)
    content = _csv(60_000)
    assert len(content) > 2 * MB
    single, error, _ = call_api("user", "upload_dataset", 1, "a.csv", content, None)
    assert error is None
    progress: list[tuple[int, int]] = []
    chunked, error, db = call_api(
        "user",
        "upload_dataset_in_parts",
        1,
        "a.csv",
        content,
        lambda done, total: progress.append((done, total)),
    )
    assert error is None
    assert chunked["first_version"]["row_count"] == single["first_version"]["row_count"] == 60_000
    assert chunked["preview_rows"] == single["preview_rows"]
    assert chunked["dataset"]["file_size"] == len(content)
    assert progress == [(i, 3) for i in range(1, 4)]  # 2,x MB cắt thành 3 phần 1 MB
    assert db["uploads"] == {}  # phiên đã được dọn


def test_upload_in_parts_rejects_files_over_the_csv_limit_and_non_csv(call_api, monkeypatch):
    monkeypatch.setattr(mock_data, "MAX_CHUNKED_UPLOAD_MB", 1)
    _, error, _ = call_api("user", "upload_dataset_in_parts", 1, "a.csv", b"x" * (MB + 1), None)
    assert error.status_code == 413 and "1 MB" in error.detail
    _, error, _ = call_api("user", "upload_dataset_in_parts", 1, "a.xlsx", b"abc", None)
    assert error.status_code == 422 and "CSV" in error.detail


def test_upload_in_parts_aborts_the_session_when_the_file_is_bad(call_api):
    _, error, db = call_api("user", "upload_dataset_in_parts", 1, "a.csv", b"id,ten\n", None)
    assert error.status_code == 422
    assert db["uploads"] == {}  # lỗi nội dung thì hủy phiên, không để rác


def test_mock_complete_reports_missing_parts_and_keeps_the_session(call_api):
    session, _, db = call_api("user", "start_chunked_upload", 1, "a.csv", 10)
    upload_id = session["upload_id"]
    _, error, db = call_api(
        "user", "send_upload_part", upload_id, 1, b"abcde", state={"_mock_db": db}
    )
    assert error is None
    _, error, db = call_api("user", "complete_chunked_upload", upload_id, 2, state={"_mock_db": db})
    assert error.status_code == 422 and "thiếu 1 phần" in error.detail
    assert upload_id in db["uploads"]


def test_a_session_cannot_be_used_by_another_user(call_api):
    session, _, db = call_api("user", "start_chunked_upload", 1, "a.csv", 10)
    _, error, _ = call_api(
        "admin", "send_upload_part", session["upload_id"], 0, b"abc", state={"_mock_db": db}
    )
    assert error.status_code == 404


def test_parts_are_retried_on_network_errors_but_not_on_backend_errors(monkeypatch):
    calls: list[int] = []

    def flaky(token, upload_id, index, content, sha256=None):
        calls.append(index)
        if len(calls) == 1:
            raise api_client.APIConnectionError("mạng chập chờn")
        return {"index": index, "received_bytes": len(content)}

    monkeypatch.setattr(
        api_client,
        "start_chunked_upload",
        lambda *a: {
            "upload_id": "u" * 32,
            "part_size_bytes": 4,
        },
    )
    monkeypatch.setattr(api_client, "send_upload_part", flaky)
    monkeypatch.setattr(api_client, "complete_chunked_upload", lambda t, u, n: {"parts": n})
    monkeypatch.setattr(api_client, "abort_chunked_upload", lambda *a: None)
    assert api_client.upload_dataset_in_parts("t", 1, "a.csv", b"abcdefgh") == {"parts": 2}
    assert calls == [0, 0, 1]  # phần 0 được gửi lại một lần

    def refused(token, upload_id, index, content, sha256=None):
        raise api_client.APIError(413, "quá lớn")

    aborted: list[str] = []
    monkeypatch.setattr(api_client, "send_upload_part", refused)
    monkeypatch.setattr(api_client, "abort_chunked_upload", lambda t, u: aborted.append(u))
    with pytest.raises(api_client.APIError):
        api_client.upload_dataset_in_parts("t", 1, "a.csv", b"abcdefgh")
    assert aborted == ["u" * 32]


def test_network_failure_after_all_retries_is_raised(monkeypatch):
    attempts: list[int] = []

    def down(token, upload_id, index, content, sha256=None):
        attempts.append(index)
        raise api_client.APIConnectionError("mất mạng")

    monkeypatch.setattr(
        api_client,
        "start_chunked_upload",
        lambda *a: {
            "upload_id": "u" * 32,
            "part_size_bytes": 4,
        },
    )
    monkeypatch.setattr(api_client, "send_upload_part", down)
    monkeypatch.setattr(api_client, "abort_chunked_upload", lambda *a: None)
    with pytest.raises(api_client.APIConnectionError):
        api_client.upload_dataset_in_parts("t", 1, "a.csv", b"abcdefgh")
    assert attempts == [0, 0, 0]  # 1 lần đầu + 2 lần thử lại rồi dừng


# ------------------------------------------------------------ mã SHA-256 và kích thước từng phần


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_client_sends_the_checksum_of_the_file_and_of_every_part(monkeypatch):
    seen = {"start": None, "parts": []}

    def start(token, project_id, filename, size, sha256=None):
        seen["start"] = (size, sha256)
        return {"upload_id": "u" * 32, "part_size_bytes": 4}

    def send(token, upload_id, index, content, sha256=None):
        seen["parts"].append((index, content, sha256))
        return {"index": index, "received_bytes": 0}

    monkeypatch.setattr(api_client, "start_chunked_upload", start)
    monkeypatch.setattr(api_client, "send_upload_part", send)
    monkeypatch.setattr(api_client, "complete_chunked_upload", lambda t, u, n: {"parts": n})
    api_client.upload_dataset_in_parts("t", 1, "a.csv", b"abcdefghij")
    assert seen["start"] == (10, _sha(b"abcdefghij"))
    assert [(i, c) for i, c, _ in seen["parts"]] == [(0, b"abcd"), (1, b"efgh"), (2, b"ij")]
    assert all(sha == _sha(content) for _, content, sha in seen["parts"])


def test_mock_rejects_a_corrupted_part_and_a_malformed_checksum(call_api):
    content = _csv(10)
    session, _, db = call_api("user", "start_chunked_upload", 1, "a.csv", len(content))
    _, error, db = call_api(
        "user",
        "send_upload_part",
        session["upload_id"],
        0,
        content,
        _sha(b"khac"),
        state={"_mock_db": db},
    )
    assert error.status_code == 422 and "bị hỏng khi truyền" in error.detail
    assert db["uploads"][session["upload_id"]]["parts"] == {}  # phần hỏng không được lưu
    _, error, _ = call_api("user", "start_chunked_upload", 1, "a.csv", 10, "khong-hop-le")
    assert error.status_code == 422 and "SHA-256" in error.detail


def test_mock_detects_swapped_parts_and_a_wrong_size_part_at_complete(call_api, monkeypatch):
    monkeypatch.setattr(mock_data, "UPLOAD_PART_MB", 1)
    content = _csv(60_000)
    size = MB
    parts = [content[i : i + size] for i in range(0, len(content), size)]
    session, _, db = call_api(
        "user", "start_chunked_upload", 1, "a.csv", len(content), _sha(content)
    )
    uid = session["upload_id"]
    swapped = [parts[1], parts[0], *parts[2:]]
    for index, part in enumerate(swapped):
        _, error, db = call_api(
            "user", "send_upload_part", uid, index, part, _sha(part), state={"_mock_db": db}
        )
        assert error is None
    _, error, db = call_api(
        "user", "complete_chunked_upload", uid, len(parts), state={"_mock_db": db}
    )
    assert error.status_code == 422 and "SHA-256" in error.detail
    assert uid in db["uploads"]  # giữ phiên để gửi lại đúng
    short = parts[0][:-10]
    _, _, db = call_api("user", "send_upload_part", uid, 0, short, state={"_mock_db": db})
    _, error, _ = call_api(
        "user", "complete_chunked_upload", uid, len(parts), state={"_mock_db": db}
    )
    assert error.status_code == 422 and "Phần 0 có" in error.detail
