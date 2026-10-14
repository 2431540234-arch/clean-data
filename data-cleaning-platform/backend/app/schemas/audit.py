"""Schema cho audit log."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    """Một dòng audit log trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    dataset_id: int | None
    action: str
    before_version: int | None
    after_version: int | None
    detail: dict[str, Any]
    created_at: datetime
