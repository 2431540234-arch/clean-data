"""Import toàn bộ model để SQLAlchemy đăng ký hết vào Base.metadata (dùng cho Alembic)."""

from app.models.audit_log import AuditLog
from app.models.base import Base
from app.models.dataset import Dataset, DatasetVersion
from app.models.project import Project
from app.models.quality_report import QualityReport
from app.models.rule import Rule
from app.models.schema_profile import SchemaProfile
from app.models.suggestion import Suggestion
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Project",
    "Dataset",
    "DatasetVersion",
    "SchemaProfile",
    "Suggestion",
    "Rule",
    "AuditLog",
    "QualityReport",
]
