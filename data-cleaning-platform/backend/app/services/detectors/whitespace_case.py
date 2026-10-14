"""Detector phát hiện khoảng trắng dư và chữ hoa/thường không nhất quán trong cột văn bản."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class WhitespaceCaseDetector(BaseDetector):
    """Phát hiện giá trị văn bản có khoảng trắng đầu/cuối/giữa dư hoặc hoa/thường lẫn lộn."""

    name = "whitespace_case"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các cột văn bản có vấn đề khoảng trắng/hoa thường.

        Gợi ý cách làm: so sánh giá trị gốc với value.strip() để phát hiện khoảng trắng
        dư; so sánh với một chuẩn hóa case (ví dụ title case) để phát hiện hoa/thường lẫn lộn.
        """
        raise NotImplementedError(
            "TODO: phát hiện khoảng trắng dư và hoa/thường không nhất quán trên cột văn bản."
        )
