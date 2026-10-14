"""Detector phát hiện email không hợp lệ hoặc viết không nhất quán (hoa/thường, khoảng trắng)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class EmailsDetector(BaseDetector):
    """Phát hiện cột email có giá trị không hợp lệ hoặc có khoảng trắng/hoa thường thừa."""

    name = "emails"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các giá trị email không hợp lệ hoặc không nhất quán.

        Gợi ý cách làm: dùng email_validator.validate_email để kiểm tra cú pháp; so sánh
        giá trị gốc với giá trị sau .strip().lower() để phát hiện khoảng trắng/hoa thường thừa.
        """
        raise NotImplementedError(
            "TODO: dùng email_validator để kiểm tra cú pháp và phát hiện email không nhất quán."
        )
