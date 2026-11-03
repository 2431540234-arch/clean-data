"""Nhóm 3 - API profiling và danh sách lỗi dữ liệu."""

from sqlalchemy import func, select

from app.models.data_issue import DataIssue
from app.models.schema_profile import SchemaProfile
from tests.conftest import FIXTURES_DIR


def _upload(client, headers, content=None, name="dirty_sample.csv"):
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()["id"]
    content = content if content is not None else (FIXTURES_DIR / name).read_bytes()
    response = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": (name, content)},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["first_version"]["id"]


def test_get_before_run_is_404_then_run_creates_profile(client, user_headers):
    version_id = _upload(client, user_headers)
    assert client.get(f"/api/v1/profiling/{version_id}", headers=user_headers).status_code == 404
    assert (
        client.get(f"/api/v1/profiling/{version_id}/issues", headers=user_headers).status_code
        == 404
    )

    run = client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["version_id"] == version_id
    columns = body["columns"]
    assert [c["column_name"] for c in columns] == [
        "ho_ten",
        "email",
        "so_dien_thoai",
        "ngay_sinh",
        "tuoi",
        "tinh_thanh",
    ]
    assert [c["column_index"] for c in columns] == list(range(6))
    by_name = {c["column_name"]: c for c in columns}
    assert by_name["email"]["inferred_type"] == "email"
    assert by_name["so_dien_thoai"]["inferred_type"] == "phone"
    assert by_name["ngay_sinh"]["inferred_type"] == "date"
    assert by_name["tuoi"]["inferred_type"] == "integer" and by_name["tuoi"]["mean_value"] > 0
    assert 0 <= by_name["tuoi"]["null_ratio"] <= 1 and by_name["tuoi"]["sample_values"]

    again = client.get(f"/api/v1/profiling/{version_id}", headers=user_headers)
    assert again.status_code == 200 and again.json() == body


def test_run_is_idempotent_and_does_not_duplicate_rows(client, db, user_headers):
    version_id = _upload(client, user_headers)
    first = client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers).json()
    issue_ids = [
        i["id"]
        for i in client.get(f"/api/v1/profiling/{version_id}/issues", headers=user_headers).json()
    ]
    second = client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers).json()
    assert first == second
    assert db.scalar(select(func.count()).select_from(SchemaProfile)) == 6
    assert [
        i["id"]
        for i in client.get(f"/api/v1/profiling/{version_id}/issues", headers=user_headers).json()
    ] == issue_ids


def test_issues_list_content_and_order(client, user_headers):
    version_id = _upload(client, user_headers)
    client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    response = client.get(f"/api/v1/profiling/{version_id}/issues", headers=user_headers)
    assert response.status_code == 200
    issues = response.json()
    assert issues, "file bẩn phải có lỗi"
    order = {"high": 0, "medium": 1, "low": 2}
    assert [order[i["severity"]] for i in issues] == sorted(order[i["severity"]] for i in issues)
    kinds = {(i["column_name"], i["kind"]) for i in issues}
    assert ("tuoi", "iqr_outlier") in kinds
    assert ("ngay_sinh", "mixed_date_format") in kinds
    assert ("email", "invalid_email") in kinds
    assert (None, "exact_duplicate_rows") in kinds
    outlier = next(i for i in issues if i["kind"] == "iqr_outlier")
    assert outlier["issue_type"] == "outlier" and outlier["affected_count"] >= 1
    assert outlier["examples"] and outlier["message"].startswith("Cột 'tuoi'")
    assert outlier["status"] == "open"


def test_clean_file_has_no_issues_but_is_not_404(client, user_headers):
    content = "ten,tuoi\nAn,29\nBình,34\nCường,37\n".encode()
    version_id = _upload(client, user_headers, content, "sach.csv")
    client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    response = client.get(f"/api/v1/profiling/{version_id}/issues", headers=user_headers)
    assert response.status_code == 200 and response.json() == []


def test_permissions_and_unknown_version(client, user_headers, other_headers, admin_headers):
    version_id = _upload(client, user_headers)
    for method, path in [
        ("post", f"/api/v1/profiling/{version_id}/run"),
        ("get", f"/api/v1/profiling/{version_id}"),
        ("get", f"/api/v1/profiling/{version_id}/issues"),
    ]:
        assert getattr(client, method)(path).status_code == 401
        assert getattr(client, method)(path, headers=other_headers).status_code == 403
        assert (
            getattr(client, method)(
                path.replace(str(version_id), "999999"), headers=user_headers
            ).status_code
            == 404
        )
    assert (
        client.post(f"/api/v1/profiling/{version_id}/run", headers=admin_headers).status_code == 200
    )


def test_missing_storage_file_gives_clear_404(client, db, user_headers):
    from app.services import storage

    version_id = _upload(client, user_headers)
    from app.models.dataset import DatasetVersion

    version = db.get(DatasetVersion, version_id)
    storage.delete_prefix(f"datasets/{version.dataset_id}")
    response = client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    assert response.status_code == 404 and "file lưu trữ" in response.json()["detail"]
    assert db.scalar(select(func.count()).select_from(DataIssue)) == 0


def test_select_sheet_discards_old_analysis(client, db, user_headers):
    import io

    import pandas as pd

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([["a", "b"], ["1", "2"]]).to_excel(writer, "S1", header=False, index=False)
        pd.DataFrame([["c"], ["x"], ["y"]]).to_excel(writer, "S2", header=False, index=False)
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=user_headers).json()[
        "id"
    ]
    upload = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": ("a.xlsx", buffer.getvalue())},
        headers=user_headers,
    ).json()
    version_id, dataset_id = upload["first_version"]["id"], upload["dataset"]["id"]
    client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers)
    assert db.scalar(select(func.count()).select_from(SchemaProfile)) == 2
    client.post(f"/api/v1/datasets/{dataset_id}/select-sheet?sheet_name=S2", headers=user_headers)
    assert client.get(f"/api/v1/profiling/{version_id}", headers=user_headers).status_code == 404
    rerun = client.post(f"/api/v1/profiling/{version_id}/run", headers=user_headers).json()
    assert [c["column_name"] for c in rerun["columns"]] == ["c"]
