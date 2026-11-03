"""Nhóm 2 - upload file, xem dataset/phiên bản, chọn sheet, danh sách dataset của project."""

import io

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.main import app
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset, DatasetVersion
from app.services import storage
from tests.conftest import FIXTURES_DIR

SAMPLE_DIR = FIXTURES_DIR.parent.parent.parent / "sample_data"


def _project(client, headers, name="Dự án thử"):
    return client.post("/api/v1/projects", json={"name": name}, headers=headers).json()["id"]


def _upload(client, headers, project_id, filename, content, content_type="text/csv"):
    return client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (filename, content, content_type)},
        headers=headers,
    )


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, header=False, index=False)
    return buffer.getvalue()


def test_upload_csv_creates_dataset_and_version(client, db, user_headers, normal_user):
    project_id = _project(client, user_headers)
    content = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()
    response = _upload(client, user_headers, project_id, "dirty_sample.csv", content)
    assert response.status_code == 200, response.text
    body = response.json()
    dataset, version = body["dataset"], body["first_version"]
    assert dataset["project_id"] == project_id and dataset["name"] == "dirty_sample"
    assert dataset["file_type"] == "csv" and dataset["file_size"] == len(content)
    assert dataset["uploaded_by"] == normal_user.id
    assert dataset["current_version_id"] == version["id"]
    assert version["version_number"] == 1 and version["parent_version_id"] is None
    assert version["row_count"] > 0 and version["column_count"] == 6
    assert body["sheet_names"] == []
    assert 0 < len(body["preview_rows"]) <= 20
    first = body["preview_rows"][0]
    assert first["row_index"] == 0 and set(first["values"]) >= {"ho_ten", "email"}
    # file gốc và phiên bản 1 đã lưu
    assert storage.load_bytes(f"datasets/{dataset['id']}/original.csv") == content
    frame = storage.load_dataframe_from_parquet(f"datasets/{dataset['id']}/v1.parquet")
    assert len(frame) == version["row_count"]


def test_upload_keeps_demo_headers_and_empty_cells_are_null(client, user_headers):
    project_id = _project(client, user_headers)
    content = (SAMPLE_DIR / "khach_hang_tieu_de_khac.csv").read_bytes()
    body = _upload(client, user_headers, project_id, "khach_hang_tieu_de_khac.csv", content).json()
    first, second = body["preview_rows"][0]["values"], body["preview_rows"][1]["values"]
    assert list(first)[:3] == ["Họ và tên", "Email liên hệ", "Số ĐT"]
    assert first["Số ĐT"] == "0901234567"
    assert second["Ghi chú"] is None  # ô trống -> null


def test_upload_writes_audit_log(client, db, user_headers):
    project_id = _project(client, user_headers)
    dataset_id = _upload(client, user_headers, project_id, "a.csv", b"a,b\n1,2\n").json()[
        "dataset"
    ]["id"]
    log = db.scalars(select(AuditLog).where(AuditLog.action == "dataset.upload")).one()
    assert log.entity_id == dataset_id and log.project_id == project_id
    assert log.new_value == {"filename": "a.csv", "rows": 1, "columns": 2}


def test_upload_requires_auth_and_project_permission(client, user_headers, other_headers):
    project_id = _project(client, user_headers)
    url = f"/api/v1/datasets/upload?project_id={project_id}"
    assert client.post(url, files={"file": ("a.csv", b"a\n1\n")}).status_code == 401
    forbidden = _upload(client, other_headers, project_id, "a.csv", b"a,b\n1,2\n")
    assert forbidden.status_code == 403
    assert _upload(client, user_headers, 999999, "a.csv", b"a\n1\n").status_code == 404


def test_upload_rejects_bad_input_without_creating_anything(client, db, user_headers):
    project_id = _project(client, user_headers)
    cases = [
        ("a.exe", b"MZ", 422),
        ("a.csv", b"", 422),
        ("a.csv", b"a,b,c\n", 422),
        ("a.xlsx", b"khong phai excel", 422),
        ("a.csv", b"PK\x03\x04" + b"\x00" * 50, 422),
    ]
    for name, content, status in cases:
        response = _upload(client, user_headers, project_id, name, content)
        assert response.status_code == status, (name, response.text)
        assert isinstance(response.json()["detail"], str)
    assert db.scalar(select(Dataset.id)) is None  # không để lại dataset rác
    response = client.post(f"/api/v1/datasets/upload?project_id={project_id}", headers=user_headers)
    assert response.status_code == 422  # thiếu file


def test_upload_too_large_returns_413(client, user_headers, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    project_id = _project(client, user_headers)
    big = b"a,b\n" + b"1,2\n" * (400 * 1024)  # ~1.6 MB
    response = _upload(client, user_headers, project_id, "big.csv", big)
    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]


def test_filename_is_sanitized(client, db, user_headers):
    project_id = _project(client, user_headers)
    response = _upload(client, user_headers, project_id, "..\\..\\etc/khách hàng.csv", b"a\n1\n")
    assert response.status_code == 200
    assert response.json()["dataset"]["original_filename"] == "khách hàng.csv"
    dataset_id = response.json()["dataset"]["id"]
    # file nằm đúng khóa do server sinh, không phụ thuộc tên người dùng
    assert storage.load_bytes(f"datasets/{dataset_id}/original.csv") == b"a\n1\n"


def test_upload_does_not_leave_dataset_when_storage_fails(client, db, user_headers, monkeypatch):
    project_id = _project(client, user_headers)

    def boom(*args, **kwargs):
        raise storage.StorageError("đĩa đầy")

    monkeypatch.setattr(storage, "save_dataframe_as_parquet", boom)
    with TestClient(app, raise_server_exceptions=False) as lenient:
        response = _upload(lenient, user_headers, project_id, "a.csv", b"a,b\n1,2\n")
    assert response.status_code == 500
    assert "đĩa đầy" not in response.text
    assert db.scalar(select(Dataset.id)) is None


def test_excel_upload_lists_sheets_and_select_sheet(client, db, user_headers):
    project_id = _project(client, user_headers)
    content = _xlsx(
        {
            "Khach": [["ten", "tuoi"], ["An", 29], ["Bình", 34]],
            "NhanSu": [["ma", "phong"], ["E1", "IT"]],
        }
    )
    response = _upload(client, user_headers, project_id, "a.xlsx", content)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sheet_names"] == ["Khach", "NhanSu"]
    assert body["dataset"]["sheet_name"] == "Khach" and body["dataset"]["file_type"] == "xlsx"
    assert body["first_version"]["row_count"] == 2
    dataset_id = body["dataset"]["id"]

    switched = client.post(
        f"/api/v1/datasets/{dataset_id}/select-sheet?sheet_name=NhanSu", headers=user_headers
    )
    assert switched.status_code == 200, switched.text
    out = switched.json()
    assert out["dataset"]["sheet_name"] == "NhanSu"
    assert out["first_version"]["id"] == body["first_version"]["id"]
    assert out["first_version"]["row_count"] == 1 and out["first_version"]["column_count"] == 2
    assert list(out["preview_rows"][0]["values"]) == ["ma", "phong"]
    frame = storage.load_dataframe_from_parquet(f"datasets/{dataset_id}/v1.parquet")
    assert list(frame.columns) == ["ma", "phong"]
    assert db.scalars(select(AuditLog).where(AuditLog.action == "dataset.select_sheet")).one()


def test_select_sheet_errors(client, db, user_headers, other_headers):
    project_id = _project(client, user_headers)
    xlsx = _upload(
        client, user_headers, project_id, "a.xlsx", _xlsx({"S1": [["a"], ["1"]]})
    ).json()["dataset"]["id"]
    csv = _upload(client, user_headers, project_id, "a.csv", b"a,b\n1,2\n").json()["dataset"]["id"]
    base = "/api/v1/datasets/{}/select-sheet?sheet_name={}"
    assert client.post(base.format(xlsx, "KhongCo"), headers=user_headers).status_code == 422
    assert client.post(base.format(csv, "S1"), headers=user_headers).status_code == 422
    assert client.post(base.format(xlsx, "S1"), headers=other_headers).status_code == 403
    assert client.post(base.format(999999, "S1"), headers=user_headers).status_code == 404
    assert (
        client.post(f"/api/v1/datasets/{xlsx}/select-sheet", headers=user_headers).status_code
        == 422
    )

    # đã có phiên bản làm sạch -> 409, không phá lịch sử
    db.add(DatasetVersion(dataset_id=xlsx, version_number=2, storage_path="datasets/x/v2.parquet"))
    db.commit()
    assert client.post(base.format(xlsx, "S1"), headers=user_headers).status_code == 409


def test_get_dataset_and_versions(client, db, user_headers, other_headers, admin_headers):
    project_id = _project(client, user_headers)
    body = _upload(client, user_headers, project_id, "a.csv", b"a,b\n1,2\n").json()
    dataset_id = body["dataset"]["id"]
    db.add(
        DatasetVersion(
            dataset_id=dataset_id,
            version_number=2,
            parent_version_id=body["first_version"]["id"],
            storage_path="datasets/x/v2.parquet",
        )
    )
    db.commit()
    url = f"/api/v1/datasets/{dataset_id}"
    assert client.get(url, headers=user_headers).json()["id"] == dataset_id
    assert client.get(url, headers=admin_headers).status_code == 200
    assert client.get(url, headers=other_headers).status_code == 403
    assert client.get("/api/v1/datasets/999999", headers=user_headers).status_code == 404
    assert client.get(url).status_code == 401
    versions = client.get(f"{url}/versions", headers=user_headers).json()
    assert [v["version_number"] for v in versions] == [1, 2]
    assert client.get(f"{url}/versions", headers=other_headers).status_code == 403


def test_list_project_datasets(client, user_headers, other_headers):
    project_id = _project(client, user_headers)
    other_project = _project(client, other_headers, "Của người khác")
    first = _upload(client, user_headers, project_id, "a.csv", b"a\n1\n").json()["dataset"]["id"]
    second = _upload(client, user_headers, project_id, "b.csv", b"a\n1\n").json()["dataset"]["id"]
    _upload(client, other_headers, other_project, "c.csv", b"a\n1\n")
    url = f"/api/v1/projects/{project_id}/datasets"
    listed = client.get(url, headers=user_headers).json()
    assert [d["id"] for d in listed] == [second, first]  # mới nhất trước
    assert client.get(url, headers=other_headers).status_code == 403
    assert client.get("/api/v1/projects/999999/datasets", headers=user_headers).status_code == 404
    assert client.get(url).status_code == 401
    empty = _project(client, user_headers, "Rỗng")
    assert client.get(f"/api/v1/projects/{empty}/datasets", headers=user_headers).json() == []
