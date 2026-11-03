"""Nhóm 8 - API quản trị (admin), thống kê hệ thống và nhật ký hoạt động."""

import time

from sqlalchemy import select

from app.models.ai_request import AIRequest
from app.models.audit_log import AuditLog
from app.models.user import User
from tests.conftest import FIXTURES_DIR

ADMIN = "/api/v1/admin"


def _actions(db, action):
    return list(db.scalars(select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id)))


# ---------------------------------------------------------------- quyền


def test_normal_user_and_anonymous_cannot_access_admin_api(client, user_headers, normal_user):
    endpoints = [
        ("get", f"{ADMIN}/users", None),
        ("get", f"{ADMIN}/stats", None),
        ("patch", f"{ADMIN}/users/{normal_user.id}", {"role": "admin"}),
        ("post", f"{ADMIN}/users/{normal_user.id}/reset-password", None),
        ("get", "/api/v1/audit/all", None),
    ]
    for method, url, body in endpoints:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(url, **kwargs).status_code == 401, url
        assert getattr(client, method)(url, headers=user_headers, **kwargs).status_code == 403, url
    assert normal_user.role == "user"  # không bị nâng quyền ngoài ý muốn


# ---------------------------------------------------------------- danh sách và cập nhật


def test_list_users(client, admin_headers, normal_user, other_user, admin_user):
    response = client.get(f"{ADMIN}/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert {u["email"] for u in users} >= {normal_user.email, other_user.email, admin_user.email}
    assert set(users[0]) == {"id", "email", "full_name", "role", "is_active", "created_at"}
    assert "password_hash" not in response.text


def test_lock_and_unlock_user_with_audit(client, db, admin_headers, admin_user, normal_user):
    url = f"{ADMIN}/users/{normal_user.id}"
    locked = client.patch(url, json={"is_active": False}, headers=admin_headers)
    assert locked.status_code == 200 and locked.json()["is_active"] is False
    unlocked = client.patch(url, json={"is_active": True}, headers=admin_headers)
    assert unlocked.json()["is_active"] is True
    lock, unlock = _actions(db, "user.lock")[0], _actions(db, "user.unlock")[0]
    assert (lock.user_id, lock.entity_id) == (admin_user.id, normal_user.id)
    assert lock.old_value == {"is_active": True} and unlock.new_value == {"is_active": True}


def test_locked_user_loses_access_immediately(client, admin_headers, user_headers, normal_user):
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 200
    client.patch(
        f"{ADMIN}/users/{normal_user.id}", json={"is_active": False}, headers=admin_headers
    )
    assert client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    assert client.get("/api/v1/projects", headers=user_headers).status_code == 401


def test_change_role_takes_effect_and_is_audited(
    client, db, admin_headers, user_headers, normal_user
):
    url = f"{ADMIN}/users/{normal_user.id}"
    assert client.get(f"{ADMIN}/users", headers=user_headers).status_code == 403
    changed = client.patch(url, json={"role": "admin"}, headers=admin_headers)
    assert changed.json()["role"] == "admin"
    assert (
        client.get(f"{ADMIN}/users", headers=user_headers).status_code == 200
    )  # token cũ, quyền mới
    log = _actions(db, "user.change_role")[0]
    assert log.old_value == {"role": "user"} and log.new_value == {"role": "admin"}


def test_update_validation_and_not_found(client, admin_headers, normal_user):
    url = f"{ADMIN}/users/{normal_user.id}"
    assert client.patch(url, json={}, headers=admin_headers).status_code == 422
    assert client.patch(url, json={"role": "superman"}, headers=admin_headers).status_code == 422
    assert (
        client.patch(
            f"{ADMIN}/users/999999", json={"is_active": False}, headers=admin_headers
        ).status_code
        == 404
    )
    assert client.patch(url, json={"is_active": "khong"}, headers=admin_headers).status_code == 422


def test_noop_update_writes_no_audit(client, db, admin_headers, normal_user):
    client.patch(
        f"{ADMIN}/users/{normal_user.id}",
        json={"role": "user", "is_active": True},
        headers=admin_headers,
    )
    assert not _actions(db, "user.lock") and not _actions(db, "user.change_role")


def test_cannot_demote_or_lock_the_last_active_admin(client, db, admin_headers, admin_user):
    url = f"{ADMIN}/users/{admin_user.id}"
    demote = client.patch(url, json={"role": "user"}, headers=admin_headers)
    assert demote.status_code == 409 and "cuối cùng" in demote.json()["detail"]
    lock = client.patch(url, json={"is_active": False}, headers=admin_headers)
    assert lock.status_code == 409
    both = client.patch(url, json={"role": "user", "is_active": False}, headers=admin_headers)
    assert both.status_code == 409
    db.refresh(admin_user)
    assert admin_user.role == "admin" and admin_user.is_active


def test_with_a_second_admin_the_first_can_be_demoted(
    client, db, admin_headers, admin_user, normal_user
):
    client.patch(f"{ADMIN}/users/{normal_user.id}", json={"role": "admin"}, headers=admin_headers)
    demote = client.patch(
        f"{ADMIN}/users/{admin_user.id}", json={"role": "user"}, headers=admin_headers
    )
    assert demote.status_code == 200 and demote.json()["role"] == "user"


def test_combined_update_is_atomic(client, db, admin_headers, admin_user, normal_user):
    """Đổi role thành công nhưng khóa thất bại (admin cuối) thì role cũng không đổi."""
    client.patch(f"{ADMIN}/users/{normal_user.id}", json={"role": "admin"}, headers=admin_headers)
    client.patch(
        f"{ADMIN}/users/{normal_user.id}", json={"is_active": False}, headers=admin_headers
    )
    response = client.patch(
        f"{ADMIN}/users/{normal_user.id}",
        json={"role": "user", "is_active": True},
        headers=admin_headers,
    )
    assert response.status_code == 200  # còn admin khác nên hợp lệ
    # kịch bản thất bại: chỉ còn admin_user là admin hoạt động
    failed = client.patch(
        f"{ADMIN}/users/{admin_user.id}",
        json={"role": "user", "is_active": False},
        headers=admin_headers,
    )
    assert failed.status_code == 409
    db.refresh(admin_user)
    assert admin_user.role == "admin"


# ---------------------------------------------------------------- reset mật khẩu


def test_reset_password_returns_temp_password_and_revokes_tokens(
    client, db, admin_headers, admin_user, user_headers, normal_user
):
    time.sleep(1.1)  # token của user được cấp trước thời điểm reset (iat tính theo giây)
    response = client.post(f"{ADMIN}/users/{normal_user.id}/reset-password", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    temp = body["new_password"]
    assert len(temp) >= 8 and "message" in body
    assert (
        client.get("/api/v1/auth/me", headers=user_headers).status_code == 401
    )  # token cũ bị thu hồi
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": normal_user.email, "password": "User12345"}
        ).status_code
        == 401
    )
    ok = client.post("/api/v1/auth/login", json={"email": normal_user.email, "password": temp})
    assert ok.status_code == 200
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {ok.json()['access_token']}"}
        ).status_code
        == 200
    )
    log = _actions(db, "user.reset_password")[0]
    assert (log.user_id, log.entity_id) == (admin_user.id, normal_user.id)
    assert temp not in str(log.new_value) + str(log.old_value)


def test_reset_password_unknown_user_and_unique_passwords(client, admin_headers, normal_user):
    assert (
        client.post(f"{ADMIN}/users/999999/reset-password", headers=admin_headers).status_code
        == 404
    )
    first = client.post(
        f"{ADMIN}/users/{normal_user.id}/reset-password", headers=admin_headers
    ).json()
    second = client.post(
        f"{ADMIN}/users/{normal_user.id}/reset-password", headers=admin_headers
    ).json()
    assert first["new_password"] != second["new_password"]


# ---------------------------------------------------------------- thống kê


def test_stats_counts(client, db, admin_headers, normal_user, other_user, admin_user, user_headers):
    other_user.is_active = False
    db.commit()
    project_id = client.post("/api/v1/projects", json={"name": "P"}, headers=user_headers).json()[
        "id"
    ]
    upload = client.post(
        f"/api/v1/datasets/upload?project_id={project_id}",
        files={"file": ("d.csv", (FIXTURES_DIR / "dirty_sample.csv").read_bytes())},
        headers=user_headers,
    ).json()
    version_id = upload["first_version"]["id"]
    client.get(f"/api/v1/quality/{version_id}", headers=user_headers)
    db.add(AIRequest(provider="anthropic", model="m", purpose="suggestions", status="success"))
    db.add(AIRequest(provider="anthropic", model="m", purpose="suggestions", status="error"))
    db.commit()

    stats = client.get(f"{ADMIN}/stats", headers=admin_headers).json()
    assert stats["total_users"] == 3 and stats["total_admins"] == 1
    assert stats["active_users"] == 2
    assert stats["total_projects"] == 1 and stats["total_datasets"] == 1
    assert stats["total_ai_calls"] == 2
    assert 0 < stats["average_quality_score"] < 100


def test_stats_with_empty_system(client, admin_headers):
    stats = client.get(f"{ADMIN}/stats", headers=admin_headers).json()
    assert stats["total_users"] == 1 and stats["total_ai_calls"] == 0
    assert stats["average_quality_score"] == 0.0


# ---------------------------------------------------------------- nhật ký


def test_audit_me_returns_only_own_newest_first(
    client, db, user_headers, other_headers, normal_user
):
    client.post("/api/v1/projects", json={"name": "A"}, headers=user_headers)
    client.post("/api/v1/projects", json={"name": "B"}, headers=user_headers)
    client.post("/api/v1/projects", json={"name": "Của người khác"}, headers=other_headers)
    mine = client.get("/api/v1/audit/me", headers=user_headers).json()
    assert [r["new_value"]["name"] for r in mine] == ["B", "A"]
    assert all(r["user_id"] == normal_user.id for r in mine)
    assert set(mine[0]) == {
        "id", "user_id", "project_id", "entity_type", "entity_id", "action",
        "old_value", "new_value", "ip_address", "created_at",
    }  # fmt: skip
    assert client.get("/api/v1/audit/me").status_code == 401


def test_audit_all_for_admin_and_pagination(client, admin_headers, user_headers, other_headers):
    for name in ("A", "B", "C"):
        client.post("/api/v1/projects", json={"name": name}, headers=user_headers)
    client.post("/api/v1/projects", json={"name": "D"}, headers=other_headers)
    everything = client.get("/api/v1/audit/all", headers=admin_headers).json()
    assert [r["new_value"]["name"] for r in everything[:4]] == ["D", "C", "B", "A"]
    page = client.get("/api/v1/audit/all?limit=2&offset=1", headers=admin_headers).json()
    assert [r["new_value"]["name"] for r in page] == ["C", "B"]
    for query in ("limit=0", "limit=99999", "offset=-1"):
        assert client.get(f"/api/v1/audit/all?{query}", headers=admin_headers).status_code == 422


def test_every_write_leaves_an_audit_trail(client, db, user_headers):
    """Mỗi thao tác ghi dữ liệu của luồng chính để lại đúng một dòng nhật ký tương ứng."""
    project = client.post("/api/v1/projects", json={"name": "P"}, headers=user_headers).json()["id"]
    upload = client.post(
        f"/api/v1/datasets/upload?project_id={project}",
        files={"file": ("d.csv", (FIXTURES_DIR / "dirty_sample.csv").read_bytes())},
        headers=user_headers,
    ).json()
    dataset, version = upload["dataset"]["id"], upload["first_version"]["id"]
    suggestions = client.post(
        "/api/v1/suggestions/generate", json={"version_id": version}, headers=user_headers
    ).json()
    client.post(
        f"/api/v1/suggestions/{suggestions[0]['id']}/decision",
        json={"decision": "accepted"},
        headers=user_headers,
    )
    client.post(
        f"/api/v1/versions/{dataset}/apply",
        json={"steps": [{"op": "drop_duplicates", "params": {}}]},
        headers=user_headers,
    )
    client.post(f"/api/v1/versions/{dataset}/undo", headers=user_headers)
    client.post(f"/api/v1/versions/{dataset}/redo", headers=user_headers)
    client.get(f"/api/v1/export/{version}/csv", headers=user_headers)
    client.delete(f"/api/v1/projects/{project}", headers=user_headers)
    actions = [a.action for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]
    assert actions == [
        "project.create",
        "dataset.upload",
        "suggestion.generate",
        "suggestion.accept",
        "version.apply_rule",
        "version.undo",
        "version.redo",
        "dataset.export",
        "project.delete",
    ]
    assert db.scalar(select(User.id)) is not None
