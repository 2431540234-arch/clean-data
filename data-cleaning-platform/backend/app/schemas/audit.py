"""Schema cho audit log."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    """Một dòng audit log trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    project_id: int | None
    entity_type: str
    entity_id: int | None
    action: str
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    ip_address: str | None
    created_at: datetime
