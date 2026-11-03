"""Schema cho lỗi dữ liệu do detector phát hiện (data_issues)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DataIssueOut(BaseModel):
    """Một nhóm lỗi dữ liệu của một cột (hoặc của cả bảng khi column_name = None)."""

    id: int
    version_id: int
    column_name: str | None
    issue_type: Literal[
        "duplicate", "missing", "outlier", "invalid_format", "type_mismatch", "inconsistent"
    ]
    severity: Literal["low", "medium", "high"]
    message: str
    affected_count: int
    examples: list[str]
    kind: str | None
    row_index: int | None
    status: Literal["open", "fixed", "ignored"]
    created_at: datetime
