"""Schema cho điểm chất lượng dữ liệu (data quality score)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class QualityReportOut(BaseModel):
    """Báo cáo điểm chất lượng của một phiên bản dataset."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    version_id: int
    score: float
    metrics: dict[str, Any]
    created_at: datetime
