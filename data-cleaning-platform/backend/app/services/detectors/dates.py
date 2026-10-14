"""Detector phát hiện cột ngày tháng bị lẫn nhiều định dạng (dd/mm/yyyy, yyyy-mm-dd...)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class DatesDetector(BaseDetector):
    """Phát hiện cột ngày tháng có nhiều định dạng không thống nhất hoặc không parse được."""

    name = "dates"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các cột ngày có định dạng không thống nhất.

        Gợi ý cách làm: với các cột được infer là "date", thử parse từng giá trị bằng
        dateutil.parser.parse, ghi nhận pattern định dạng phát hiện được (dd/mm/yyyy vs
        yyyy-mm-dd) và các giá trị không parse được.
        """
        raise NotImplementedError(
            "TODO: thử parse từng giá trị cột ngày, phát hiện định dạng lẫn nhau / lỗi parse."
        )
