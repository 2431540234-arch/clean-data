"""Cô lập dữ liệu: user A không đọc/sửa/xóa được bất kỳ thứ gì của user B (admin thì được)."""

import pytest

from tests.conftest import FIXTURES_DIR

DIRTY = (FIXTURES_DIR / "dirty_sample.csv").read_bytes()
STEP = {"steps": [{"op": "trim_whitespace", "column": "email", "params": {}}]}


@pytest.fixture
def victim(client, user_headers):
    """Toàn bộ dữ liệu của user B ("nạn nhân"): project, dataset, phiên bản, gợi ý, rule."""
    project = client.post("/api/v1/projects", json={"name": "Bí mật"}, headers=user_headers).json()
    upload = client.post(
        f"/api/v1/datasets/upload?project_id={project['id']}",
        files={"file": ("bi_mat.csv", DIRTY)},
        headers=user_headers,
    ).json()
    version_id = upload["first_version"]["id"]
    suggestion = client.post(
        "/api/v1/suggestions/generate", json={"version_id": version_id}, headers=user_headers
    ).json()[0]
    rule = client.post(
        f"/api/v1/rules/by-project/{project['id']}",
        json={"name": "R", "rule_set": STEP},
        headers=user_headers,
    ).json()
    return {
        "project": project["id"],
        "dataset": upload["dataset"]["id"],
        "version": version_id,
        "suggestion": suggestion["id"],
        "rule": rule["id"],
    }


def _requests(v):
    """Mọi endpoint chạm vào dữ liệu của một project/dataset/version/suggestion/rule."""
    p, d, ver = v["project"], v["dataset"], v["version"]
    return [
        ("get", f"/api/v1/projects/{p}", None),
        ("put", f"/api/v1/projects/{p}", {"name": "Bị chiếm"}),
        ("delete", f"/api/v1/projects/{p}", None),
        ("get", f"/api/v1/projects/{p}/datasets", None),
        ("post", f"/api/v1/datasets/upload?project_id={p}", "UPLOAD"),
        ("get", f"/api/v1/datasets/{d}", None),
        ("get", f"/api/v1/datasets/{d}/versions", None),
        ("get", f"/api/v1/datasets/{d}/versions/{ver}/rows", None),
        ("post", f"/api/v1/datasets/{d}/select-sheet?sheet_name=S", None),
        ("post", f"/api/v1/profiling/{ver}/run", None),
        ("get", f"/api/v1/profiling/{ver}", None),
        ("get", f"/api/v1/profiling/{ver}/issues", None),
        ("post", f"/api/v1/mapping/{ver}/suggest", ["ho_ten"]),
        ("post", "/api/v1/suggestions/generate", {"version_id": ver}),
        ("get", f"/api/v1/suggestions/by-version/{ver}", None),
        ("post", f"/api/v1/suggestions/{v['suggestion']}/decision", {"decision": "accepted"}),
        ("post", "/api/v1/preview", {"version_id": ver, "rule_set": STEP}),
        ("post", f"/api/v1/versions/{d}/apply", STEP),
        ("post", f"/api/v1/versions/{d}/undo", None),
        ("post", f"/api/v1/versions/{d}/redo", None),
        ("post", f"/api/v1/versions/{d}/restore/{ver}", None),
        ("get", f"/api/v1/quality/{ver}", None),
        ("get", f"/api/v1/export/{ver}/csv", None),
        ("get", f"/api/v1/export/{ver}/excel", None),
        ("get", f"/api/v1/rules/by-project/{p}", None),
        ("post", f"/api/v1/rules/by-project/{p}", {"name": "X", "rule_set": STEP}),
        ("delete", f"/api/v1/rules/{v['rule']}", None),
    ]


def _send(client, method, url, body, headers):
    if body == "UPLOAD":
        return client.post(url, files={"file": ("x.csv", b"a\n1\n")}, headers=headers)
    kwargs = {"json": body} if body is not None else {}
    return getattr(client, method)(url, headers=headers, **kwargs)


def test_other_user_gets_403_on_every_endpoint(client, victim, other_headers):
    for method, url, body in _requests(victim):
        response = _send(client, method, url, body, other_headers)
        assert response.status_code == 403, (method, url, response.status_code, response.text)
        assert "Bí mật" not in response.text and "bi_mat" not in response.text


def test_anonymous_gets_401_on_every_endpoint(client, victim):
    for method, url, body in _requests(victim):
        assert _send(client, method, url, body, None).status_code == 401, (method, url)


def test_forbidden_requests_changed_nothing(client, victim, user_headers, other_headers):
    for method, url, body in _requests(victim):
        _send(client, method, url, body, other_headers)
    project = client.get(f"/api/v1/projects/{victim['project']}", headers=user_headers).json()
    assert project["name"] == "Bí mật"
    versions = client.get(f"/api/v1/datasets/{victim['dataset']}/versions", headers=user_headers)
    assert len(versions.json()) == 1
    assert (
        len(
            client.get(f"/api/v1/rules/by-project/{victim['project']}", headers=user_headers).json()
        )
        == 1
    )
    suggestions = client.get(
        f"/api/v1/suggestions/by-version/{victim['version']}", headers=user_headers
    )
    assert all(s["status"] == "pending" for s in suggestions.json())


def test_listings_never_include_other_users_data(client, victim, other_headers):
    assert client.get("/api/v1/projects", headers=other_headers).json() == []
    assert client.get("/api/v1/audit/me", headers=other_headers).json() == []


def test_admin_can_read_everything(client, victim, admin_headers):
    ok = [
        ("get", f"/api/v1/projects/{victim['project']}"),
        ("get", f"/api/v1/datasets/{victim['dataset']}"),
        ("get", f"/api/v1/profiling/{victim['version']}/issues"),
        ("get", f"/api/v1/quality/{victim['version']}"),
        ("get", f"/api/v1/export/{victim['version']}/csv"),
    ]
    for method, url in ok:
        assert getattr(client, method)(url, headers=admin_headers).status_code == 200, url
    assert len(client.get("/api/v1/projects", headers=admin_headers).json()) == 1


def test_unknown_ids_are_404_not_403(client, other_headers):
    for url in ("/api/v1/projects/999999", "/api/v1/datasets/999999", "/api/v1/quality/999999"):
        assert client.get(url, headers=other_headers).status_code == 404
