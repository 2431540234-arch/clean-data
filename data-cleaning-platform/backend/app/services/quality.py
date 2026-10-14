"""Tính Data Quality Score cho một phiên bản dataset."""

import pandas as pd

from app.schemas.quality import QualityReportOut

# Trọng số các tiêu chí tính điểm chất lượng, xem chi tiết công thức ở docs/quality_score.md.
QUALITY_WEIGHTS = {
    "completeness": 0.3,
    "uniqueness": 0.2,
    "validity": 0.3,
    "consistency": 0.2,
}


def compute_quality_score(df: pd.DataFrame) -> QualityReportOut:
    """Tính điểm chất lượng tổng hợp (0-100) dựa trên completeness/uniqueness/validity/consistency.

    Gợi ý cách làm: tính từng chỉ số con (ví dụ completeness = 1 - tỉ lệ null trung bình),
    nhân với QUALITY_WEIGHTS rồi cộng lại, scale về thang 0-100.
    """
    raise NotImplementedError(
        "TODO: tính các chỉ số con rồi tổng hợp theo QUALITY_WEIGHTS thành điểm 0-100."
    )
