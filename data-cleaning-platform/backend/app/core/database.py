"""Khởi tạo SQLAlchemy engine và SessionLocal dùng chung cho toàn backend."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_session() -> Generator[Session, None, None]:
    """Tạo một session DB mới, đảm bảo đóng lại sau khi dùng xong.

    Dùng trực tiếp ngoài FastAPI (script, worker). Trong API nên dùng
    ``app.core.deps.get_db`` để FastAPI tự quản lý vòng đời session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
