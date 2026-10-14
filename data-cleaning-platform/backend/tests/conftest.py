"""Fixture chung cho test suite: DB test riêng biệt, TestClient, user & admin mẫu."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.models.user import User

_base_url = make_url(settings.DATABASE_URL)
_test_url = _base_url.set(database=_base_url.database + "_test")

_engine = create_engine(_test_url, future=True)
_TestSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _setup_test_database() -> Generator[None, None, None]:
    """Tạo toàn bộ bảng trong DB test trước khi chạy test suite, xóa sau khi xong."""
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Cung cấp một DB session cho mỗi test, xóa sạch dữ liệu các bảng sau khi test xong."""
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """TestClient của FastAPI app, override get_db để dùng DB test."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def normal_user(db: Session) -> User:
    """Tạo một user thường mẫu để dùng trong test."""
    user = User(
        email="user@example.com",
        password_hash=hash_password("User1234!"),
        full_name="Người Dùng Thường",
        role="user",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    """Tạo một user admin mẫu để dùng trong test."""
    user = User(
        email="admin@example.com",
        password_hash=hash_password("Admin1234!"),
        full_name="Quản Trị Viên",
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
