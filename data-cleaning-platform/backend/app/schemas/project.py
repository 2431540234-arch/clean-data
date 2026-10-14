"""Schema cho project (dự án làm sạch dữ liệu)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Dữ liệu tạo project mới."""

    name: str = Field(min_length=1, max_length=255)


class ProjectUpdate(BaseModel):
    """Dữ liệu cập nhật project."""

    name: str = Field(min_length=1, max_length=255)


class ProjectOut(BaseModel):
    """Thông tin project trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime
