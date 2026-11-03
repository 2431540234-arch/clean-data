"""Schema cho project (dự án làm sạch dữ liệu)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Tên dự án không được để trống.")
    return value


class ProjectCreate(BaseModel):
    """Dữ liệu tạo project mới."""

    name: str = Field(min_length=1, max_length=255)

    _strip = field_validator("name")(_clean_name)


class ProjectUpdate(BaseModel):
    """Dữ liệu cập nhật project."""

    name: str = Field(min_length=1, max_length=255)

    _strip = field_validator("name")(_clean_name)


class ProjectOut(BaseModel):
    """Thông tin project trả về cho client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime
    # Chỉ có trong GET /projects (danh sách); thiếu thì frontend ẩn chỉ số tương ứng.
    dataset_count: int | None = None
    average_quality_score: float | None = None
