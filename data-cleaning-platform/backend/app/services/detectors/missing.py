"""Detector phát hiện dữ liệu thiếu (null, chuỗi rỗng, các token coi như null)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class MissingDetector(BaseDetector):
    """Phát hiện các cột/dòng có dữ liệu thiếu, dựa trên app.data.null_tokens.json."""

    name = "missing"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho mỗi cột có tỉ lệ thiếu dữ liệu vượt ngưỡng.

        Gợi ý cách làm: chuẩn hóa các giá trị thuộc null_tokens.json thành NaN trước khi
        tính tỉ lệ; severity tăng theo null_ratio (ví dụ > 0.5 là "high").
        """
        raise NotImplementedError(
            "TODO: tính tỉ lệ thiếu dữ liệu mỗi cột (gồm cả null-token) và sinh DetectionIssue."
        )
