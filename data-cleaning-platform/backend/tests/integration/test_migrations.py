"""Migration trên DB trống: upgrade head, khớp model (như `alembic check`), downgrade và lại."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from app.core.config import settings
from app.models import Base
from tests.conftest import ensure_database

BACKEND_DIR = Path(__file__).parents[2]


@pytest.fixture
def empty_database(monkeypatch):
    """Một DB trống riêng cho test migration; env.py của Alembic đọc settings.DATABASE_URL."""
    base = make_url(settings.DATABASE_URL)
    url = base.set(database=base.database + "_migration")
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    ensure_database(url)
    monkeypatch.setattr(settings, "DATABASE_URL", url.render_as_string(hide_password=False))
    engine = create_engine(url)
    yield engine, url
    engine.dispose()
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
    admin.dispose()


def _config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _diff(engine) -> list:
    with engine.connect() as conn:
        return compare_metadata(MigrationContext.configure(conn), Base.metadata)


def test_single_head():
    assert len(ScriptDirectory.from_config(_config()).get_heads()) == 1


def test_upgrade_matches_models_and_roundtrips(empty_database):
    engine, _ = empty_database
    config = _config()
    command.upgrade(config, "head")
    tables = set(inspect(engine).get_table_names())
    assert {"users", "projects", "data_issues", "audit_logs", "quality_reports"} <= tables
    assert len(tables - {"alembic_version"}) == 16
    assert _diff(engine) == []  # tương đương `alembic check`: không còn thay đổi nào cần tạo

    command.downgrade(config, "0001")
    command.upgrade(config, "head")
    assert _diff(engine) == []

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
