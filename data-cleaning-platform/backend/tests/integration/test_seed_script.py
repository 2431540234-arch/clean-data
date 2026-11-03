"""scripts/seed.py: tạo tài khoản demo, chạy lại không tạo trùng, từ chối ở production."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import verify_password
from app.models.dataset import Dataset
from app.models.project import Project
from app.models.user import User

SEED_PATH = Path(__file__).parents[2] / "scripts" / "seed.py"


@pytest.fixture
def seed(db, monkeypatch, capsys):
    spec = importlib.util.spec_from_file_location("seed_script", SEED_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "SessionLocal", lambda: db)
    return module


def test_creates_two_demo_accounts_with_hashed_passwords(seed, db):
    assert seed.main() == 0
    users = {u.email: u for u in db.scalars(select(User))}
    assert set(users) == {"admin@example.com", "user@example.com"}
    assert users["admin@example.com"].role == "admin"
    assert users["user@example.com"].role == "user"
    assert users["user@example.com"].password_hash != "User12345"  # không lưu mật khẩu thuần
    assert verify_password("User12345", users["user@example.com"].password_hash)


def test_second_run_does_not_duplicate(seed, db):
    seed.main()
    seed.main()
    assert db.scalar(select(func.count()).select_from(User)) == 2


def test_seeds_demo_project_with_sample_dataset_once(seed, db):
    seed.main()
    seed.main()
    projects = list(db.scalars(select(Project)))
    assert [p.name for p in projects] == ["Khách hàng 2026"]
    datasets = list(db.scalars(select(Dataset)))
    assert len(datasets) == 1 and datasets[0].current_version_id is not None
    assert datasets[0].current_version.row_count > 20


def test_refuses_to_run_in_production(seed, db, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert seed.main() == 1
    assert db.scalar(select(func.count()).select_from(User)) == 0
