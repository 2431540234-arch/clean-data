"""Detector phát hiện outlier trên các cột số bằng IQR hoặc Z-score."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class OutliersDetector(BaseDetector):
    """Phát hiện giá trị bất thường (outlier) trên các cột số, ví dụ tuổi, số tiền."""

    name = "outliers"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các dòng là outlier trên từng cột số.

        Gợi ý cách làm IQR: Q1, Q3 = quantile(0.25/0.75); ngoài [Q1 - 1.5*IQR, Q3 + 1.5*IQR]
        là outlier. Gợi ý cách làm Z-score: |（x - mean) / std| > 3 là outlier.
        """
        raise NotImplementedError(
            "TODO: xác định cột số, tính ngưỡng IQR/Z-score, sinh DetectionIssue cho outlier."
        )
