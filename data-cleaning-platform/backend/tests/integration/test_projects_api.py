"""Nhóm 1 - API projects: CRUD, phân quyền, dữ liệu sai, nhật ký, dọn file khi xóa."""

from sqlalchemy import select

from app.models.audit_log import AuditLog
from app.models.dataset import Dataset
from app.models.project import Project
from app.services import storage


def _create(client, headers, name="Khách hàng 2026"):
    response = client.post("/api/v1/projects", json={"name": name}, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_create_and_get_project(client, user_headers, normal_user):
    created = _create(client, user_headers)
    assert created["name"] == "Khách hàng 2026"
    assert created["owner_id"] == normal_user.id
    got = client.get(f"/api/v1/projects/{created['id']}", headers=user_headers)
    assert got.status_code == 200 and got.json()["id"] == created["id"]


def test_name_is_trimmed_and_blank_name_rejected(client, user_headers):
    assert _create(client, user_headers, "  Dự án A  ")["name"] == "Dự án A"
    for bad in ("", "   ", "x" * 256):
        response = client.post("/api/v1/projects", json={"name": bad}, headers=user_headers)
        assert response.status_code == 422
    assert client.post("/api/v1/projects", json={}, headers=user_headers).status_code == 422


def test_list_only_returns_own_projects_with_dataset_count(
    client, db, user_headers, other_headers, normal_user
):
    mine = _create(client, user_headers, "Của tôi")
    _create(client, other_headers, "Của người khác")
    db.add(Dataset(project_id=mine["id"], name="d", original_filename="d.csv", file_type="csv"))
    db.add(Dataset(project_id=mine["id"], name="e", original_filename="e.csv", file_type="csv"))
    db.commit()
    listed = client.get("/api/v1/projects", headers=user_headers).json()
    assert [p["name"] for p in listed] == ["Của tôi"]
    assert listed[0]["dataset_count"] == 2


def test_admin_sees_all_projects(client, user_headers, other_headers, admin_headers):
    _create(client, user_headers)
    _create(client, other_headers)
    assert len(client.get("/api/v1/projects", headers=admin_headers).json()) == 2


def test_other_user_gets_403_and_missing_gets_404(client, user_headers, other_headers):
    project_id = _create(client, user_headers)["id"]
    url = f"/api/v1/projects/{project_id}"
    assert client.get(url, headers=other_headers).status_code == 403
    assert client.put(url, json={"name": "x"}, headers=other_headers).status_code == 403
    assert client.delete(url, headers=other_headers).status_code == 403
    assert client.get("/api/v1/projects/999999", headers=user_headers).status_code == 404
    # sau các lần bị từ chối, dữ liệu vẫn nguyên
    assert client.get(url, headers=user_headers).json()["name"] == "Khách hàng 2026"


def test_admin_can_update_and_delete_any_project(client, user_headers, admin_headers):
    project_id = _create(client, user_headers)["id"]
    url = f"/api/v1/projects/{project_id}"
    assert client.put(url, json={"name": "Đổi bởi admin"}, headers=admin_headers).status_code == 200
    assert client.delete(url, headers=admin_headers).status_code == 200


def test_requires_authentication(client):
    assert client.get("/api/v1/projects").status_code == 401
    assert client.post("/api/v1/projects", json={"name": "x"}).status_code == 401


def test_update_changes_name(client, user_headers):
    project_id = _create(client, user_headers)["id"]
    response = client.put(
        f"/api/v1/projects/{project_id}", json={"name": "Tên mới"}, headers=user_headers
    )
    assert response.status_code == 200 and response.json()["name"] == "Tên mới"
    assert (
        client.put(
            f"/api/v1/projects/{project_id}", json={"name": " "}, headers=user_headers
        ).status_code
        == 422
    )


def test_delete_removes_project_datasets_and_files(client, db, user_headers):
    project_id = _create(client, user_headers)["id"]
    dataset = Dataset(project_id=project_id, name="d", original_filename="d.csv", file_type="csv")
    db.add(dataset)
    db.commit()
    storage.save_bytes(f"datasets/{dataset.id}/original.csv", b"a\n1\n")
    dataset_id = dataset.id

    response = client.delete(f"/api/v1/projects/{project_id}", headers=user_headers)
    assert response.status_code == 200 and "message" in response.json()

    db.expire_all()
    assert db.get(Project, project_id) is None
    assert db.get(Dataset, dataset_id) is None
    try:
        storage.load_bytes(f"datasets/{dataset_id}/original.csv")
        raise AssertionError("file lưu trữ phải bị xóa")
    except storage.StorageError:
        pass
    assert client.get(f"/api/v1/projects/{project_id}", headers=user_headers).status_code == 404


def test_each_write_is_audited(client, db, user_headers, normal_user):
    project_id = _create(client, user_headers)["id"]
    client.put(f"/api/v1/projects/{project_id}", json={"name": "B"}, headers=user_headers)
    client.delete(f"/api/v1/projects/{project_id}", headers=user_headers)
    logs = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()
    assert [log.action for log in logs] == ["project.create", "project.update", "project.delete"]
    assert all(log.user_id == normal_user.id and log.entity_id == project_id for log in logs)
    assert logs[1].old_value == {"name": "Khách hàng 2026"} and logs[1].new_value == {"name": "B"}


def test_failed_request_writes_no_audit(client, db, user_headers, other_headers):
    project_id = _create(client, user_headers)["id"]
    client.delete(f"/api/v1/projects/{project_id}", headers=other_headers)
    actions = [log.action for log in db.scalars(select(AuditLog))]
    assert actions == ["project.create"]
