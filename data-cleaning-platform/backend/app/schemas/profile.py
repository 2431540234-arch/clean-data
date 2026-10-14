"""Schema cho kết quả profiling schema (thống kê từng cột)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SchemaProfileOut(BaseModel):
    """Thống kê của một cột: kiểu dữ liệu suy luận, tỉ lệ null, tỉ lệ unique, mẫu giá trị."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    column_name: str
    inferred_type: str
    null_ratio: float
    unique_ratio: float
    sample_values: list[Any]
    created_at: datetime


class ProfilingResult(BaseModel):
    """Kết quả chạy profiling cho toàn bộ dataset version."""

    version_id: int
    columns: list[SchemaProfileOut]
