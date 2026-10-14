"""Schema cho kết quả profiling schema (thống kê từng cột)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SchemaProfileOut(BaseModel):
    """Thống kê một cột: kiểu suy luận, số lượng/tỉ lệ null và unique, min/max/mean, mẫu giá trị."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    column_name: str
    column_index: int | None
    inferred_type: str
    null_count: int
    unique_count: int
    null_ratio: float
    unique_ratio: float
    min_value: str | None
    max_value: str | None
    mean_value: float | None
    sample_values: list[Any]
    detected_format: str | None
    created_at: datetime


class ProfilingResult(BaseModel):
    """Kết quả chạy profiling cho toàn bộ dataset version."""

    version_id: int
    columns: list[SchemaProfileOut]
