"""Nhóm 0 (hạ tầng): helper quyền sở hữu, xử lý lỗi chung, IP client, nhật ký, cấu hình an toàn."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.requests import Request

from app.core import config as config_module
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.request_info import client_ip
from app.main import app
from app.models.audit_log import AuditLog
from app.models.dataset import Dataset, DatasetVersion
from app.models.project import Project
from app.models.suggestion import Suggestion
from app.services import access
from app.services.audit import log_action


def _make_chain(db, owner):
    """project -> dataset -> version -> suggestion thuộc về `owner`."""
    project = Project(name="Dự án", owner_id=owner.id)
    db.add(project)
    db.flush()
    dataset = Dataset(project_id=project.id, name="d", original_filename="d.csv", file_type="csv")
    db.add(dataset)
    db.flush()
    version = DatasetVersion(dataset_id=dataset.id, version_number=1, storage_path="datasets/1/v1")
    db.add(version)
    db.flush()
    suggestion = Suggestion(
        version_id=version.id,
        source="rule_engine",
        proposed_rule={"steps": []},
        explanation="x",
    )
    db.add(suggestion)
    db.commit()
    return project, dataset, version, suggestion


# ---------------------------------------------------------------- quyền sở hữu


def test_owner_and_admin_can_reach_every_level(db, normal_user, admin_user):
    project, dataset, version, suggestion = _make_chain(db, normal_user)
    for user in (normal_user, admin_user):
        assert access.get_owned_project(db, user, project.id).id == project.id
        assert access.get_owned_dataset(db, user, dataset.id).id == dataset.id
        assert access.get_owned_version(db, user, version.id).id == version.id
        assert access.get_owned_suggestion(db, user, suggestion.id).id == suggestion.id


def test_other_user_is_forbidden_at_every_level(db, normal_user, other_user):
    project, dataset, version, suggestion = _make_chain(db, normal_user)
    for getter, resource in [
        (access.get_owned_project, project),
        (access.get_owned_dataset, dataset),
        (access.get_owned_version, version),
        (access.get_owned_suggestion, suggestion),
    ]:
        with pytest.raises(ForbiddenError):
            getter(db, other_user, resource.id)


def test_missing_resources_are_not_found(db, normal_user):
    for getter in (
        access.get_owned_project,
        access.get_owned_dataset,
        access.get_owned_version,
        access.get_owned_suggestion,
    ):
        with pytest.raises(NotFoundError):
            getter(db, normal_user, 999999)


# ---------------------------------------------------------------- lỗi chung


def test_unexpected_error_returns_generic_message_without_internals(db):
    def boom():
        raise RuntimeError("mật khẩu db = hunter2, file C:/secret.py")

    app.add_api_route("/__boom", boom)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/__boom")
    finally:
        app.router.routes = [r for r in app.router.routes if getattr(r, "path", "") != "/__boom"]
    assert response.status_code == 500
    assert response.json() == {"detail": "Máy chủ gặp sự cố. Vui lòng thử lại sau."}
    assert "hunter2" not in response.text and "secret" not in response.text


def test_app_error_keeps_vietnamese_message(client):
    response = client.get("/api/v1/auth/me")  # thiếu token
    assert response.status_code == 401
    assert response.json() == {"detail": "Thiếu token xác thực."}


# ---------------------------------------------------------------- IP client


def _request(headers: dict[str, str], host: str = "10.0.0.5") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 1234),
    }
    return Request(scope)


def test_client_ip_ignores_forwarded_header_by_default(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4"})) == "10.0.0.5"


def test_client_ip_uses_first_forwarded_address_when_trusted(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert client_ip(_request({"X-Forwarded-For": "1.2.3.4, 9.9.9.9"})) == "1.2.3.4"
    assert client_ip(_request({})) == "10.0.0.5"


def test_client_ip_truncates_to_column_size(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert len(client_ip(_request({"X-Forwarded-For": "x" * 200}))) == 45


# ---------------------------------------------------------------- audit


def test_log_action_commits_by_default(db, normal_user):
    log_action(db, normal_user.id, "project.create", "project", 1)
    db.rollback()
    assert db.scalar(select(AuditLog.action)) == "project.create"


def test_log_action_without_commit_rolls_back_with_the_operation(db, normal_user):
    log_action(db, normal_user.id, "project.create", "project", 1, commit=False)
    db.rollback()  # thao tác chính thất bại -> nhật ký cũng không tồn tại
    assert db.scalar(select(AuditLog.id)) is None


# ---------------------------------------------------------------- cấu hình


def test_default_cors_is_not_wildcard():
    assert "*" not in config_module.Settings.model_fields["CORS_ORIGINS"].default


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"JWT_SECRET": config_module.DEFAULT_JWT_SECRET}, "JWT_SECRET"),
        ({"JWT_SECRET": "bi-mat-du-dai-va-ngau-nhien", "CORS_ORIGINS": '["*"]'}, "CORS_ORIGINS"),
    ],
)
def test_production_refuses_unsafe_config(monkeypatch, env, message):
    monkeypatch.setenv("ENVIRONMENT", "production")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(RuntimeError, match=message):
        config_module.validate_runtime_config(config_module.Settings())


def test_production_accepts_safe_config_and_dev_accepts_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "bi-mat-du-dai-va-ngau-nhien")
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com"]')
    config_module.validate_runtime_config(config_module.Settings())
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("JWT_SECRET", config_module.DEFAULT_JWT_SECRET)
    config_module.validate_runtime_config(config_module.Settings())  # dev: không chặn
