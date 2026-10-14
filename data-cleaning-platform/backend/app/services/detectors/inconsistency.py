"""Detector phát hiện biến thể giá trị không nhất quán, ví dụ "HCM" / "TP.HCM" / "Hồ Chí Minh"."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class InconsistencyDetector(BaseDetector):
    """Phát hiện các giá trị là biến thể của nhau (viết tắt, bỏ dấu, sai chính tả nhẹ)."""

    name = "inconsistency"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các nhóm giá trị khả năng là biến thể của nhau.

        Gợi ý cách làm: dùng Unidecode để bỏ dấu + lowercase rồi nhóm giá trị theo
        chuỗi chuẩn hóa; nếu một nhóm chuẩn hóa ứng với nhiều giá trị gốc khác nhau
        thì đó là dấu hiệu không nhất quán (ví dụ dựa vào app.data.provinces_vn.json
        cho cột tỉnh/thành).
        """
        raise NotImplementedError(
            "TODO: chuẩn hóa giá trị (bỏ dấu, lowercase) rồi nhóm để phát hiện biến thể."
        )
