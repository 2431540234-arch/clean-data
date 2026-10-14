"""Detector phát hiện số điện thoại không hợp lệ hoặc nhiều kiểu định dạng (số điện thoại VN)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class PhonesDetector(BaseDetector):
    """Phát hiện cột số điện thoại có giá trị không hợp lệ hoặc không đồng nhất định dạng."""

    name = "phones"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các giá trị số điện thoại không hợp lệ.

        Gợi ý cách làm: dùng phonenumbers.parse(value, "VN") rồi
        phonenumbers.is_valid_number(); ghi nhận các dòng không hợp lệ hoặc có
        định dạng khác nhau (có/không mã vùng, có/không khoảng trắng hoặc dấu gạch).
        """
        raise NotImplementedError(
            "TODO: dùng phonenumbers để kiểm tra tính hợp lệ của số điện thoại VN."
        )
