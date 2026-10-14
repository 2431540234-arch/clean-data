"""Base class chung cho toàn bộ SQLAlchemy ORM model."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative dùng chung; Alembic đọc ``Base.metadata`` để sinh migration."""
