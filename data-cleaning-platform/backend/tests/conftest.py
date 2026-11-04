"""Fixture chung cho test suite: DB test riêng biệt, TestClient, user mẫu, token, lưu trữ tạm.

DB test chỉ được tạo khi một test thực sự cần (`db`/`client`), nên unit test thuần (rule engine,
detector, profiler...) chạy được mà không cần PostgreSQL.
"""

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.base import Base
from app.models.user import User

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_base_url = make_url(settings.DATABASE_URL)
_test_url = _base_url.set(database=_base_url.database + "_test")


def ensure_database(url) -> None:
    """Tạo database `url` nếu chưa có (máy mới chỉ cần Postgres chạy, khỏi tạo DB test tay)."""
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        admin.dispose()


_engine = create_engine(_test_url, future=True)
_TestSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session")
def _test_database() -> Generator[None, None, None]:
    """Tạo toàn bộ bảng trong DB test (một lần cho cả phiên), xóa sau khi xong."""
    ensure_database(_test_url)
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture(autouse=True)
def _isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mọi test ghi file vào thư mục tạm (driver local), không bao giờ đụng thư mục thật/S3."""
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "STORAGE_LOCAL_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "UPLOAD_TMP_DIR", str(tmp_path / "tmp_uploads"))


@pytest.fixture(autouse=True)
def _no_real_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test không bao giờ gọi AI thật (kể cả khi máy dev có khóa trong .env)."""
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")


@pytest.fixture
def db(_test_database: None) -> Generator[Session, None, None]:
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


def _make_user(db: Session, email: str, password: str, full_name: str, role: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def normal_user(db: Session) -> User:
    """Một user thường mẫu."""
    return _make_user(db, "user@example.com", "User1234!", "Người Dùng Thường", "user")


@pytest.fixture
def other_user(db: Session) -> User:
    """Một user thường thứ hai (để kiểm tra cô lập dữ liệu giữa người dùng)."""
    return _make_user(db, "other@example.com", "Other1234!", "Người Dùng Khác", "user")


@pytest.fixture
def admin_user(db: Session) -> User:
    """Một user admin mẫu."""
    return _make_user(db, "admin@example.com", "Admin1234!", "Quản Trị Viên", "admin")


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    """Hàm tạo header Authorization hợp lệ cho một user."""

    def _headers(user: User) -> dict[str, str]:
        token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
        return {"Authorization": f"Bearer {token}"}

    return _headers


@pytest.fixture
def user_headers(normal_user: User, auth_headers: Callable[[User], dict[str, str]]) -> dict:
    return auth_headers(normal_user)


@pytest.fixture
def other_headers(other_user: User, auth_headers: Callable[[User], dict[str, str]]) -> dict:
    return auth_headers(other_user)


@pytest.fixture
def admin_headers(admin_user: User, auth_headers: Callable[[User], dict[str, str]]) -> dict:
    return auth_headers(admin_user)
