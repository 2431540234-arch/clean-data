"""Detector phát hiện dòng trùng lặp tuyệt đối và trùng lặp gần đúng (fuzzy)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue


class DuplicatesDetector(BaseDetector):
    """Phát hiện dòng trùng lặp tuyệt đối (df.duplicated()) và gần đúng (rapidfuzz)."""

    name = "duplicates"

    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho các nhóm dòng trùng lặp.

        Gợi ý cách làm:
        - Trùng tuyệt đối: df[df.duplicated(keep=False)].
        - Trùng gần đúng: dùng rapidfuzz.fuzz.ratio so sánh theo cặp trên các cột
          định danh (ví dụ họ tên, email) với ngưỡng ví dụ >= 90.
        """
        raise NotImplementedError(
            "TODO: phát hiện trùng tuyệt đối bằng duplicated(), trùng gần đúng bằng rapidfuzz."
        )
