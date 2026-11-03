"""Các detector phát hiện lỗi dữ liệu: thiếu, trùng lặp, outlier, sai định dạng..."""

import logging

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue
from app.services.detectors.dates import DatesDetector
from app.services.detectors.duplicates import DuplicatesDetector
from app.services.detectors.emails import EmailsDetector
from app.services.detectors.inconsistency import InconsistencyDetector
from app.services.detectors.missing import MissingDetector
from app.services.detectors.outliers import OutliersDetector
from app.services.detectors.phones import PhonesDetector
from app.services.detectors.whitespace_case import WhitespaceCaseDetector

logger = logging.getLogger(__name__)

ALL_DETECTORS: list[type[BaseDetector]] = [
    MissingDetector,
    DuplicatesDetector,
    OutliersDetector,
    DatesDetector,
    PhonesDetector,
    EmailsDetector,
    WhitespaceCaseDetector,
    InconsistencyDetector,
]

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def run_all_detectors(
    df: pd.DataFrame, column_types: dict[str, str] | None = None
) -> list[DetectionIssue]:
    """Chạy mọi detector; một detector lỗi không làm hỏng các detector còn lại.

    Kết quả sắp xếp từ nghiêm trọng nhất, rồi theo số dòng bị ảnh hưởng giảm dần.
    """
    issues: list[DetectionIssue] = []
    for detector_class in ALL_DETECTORS:
        try:
            issues.extend(detector_class().detect(df, column_types))
        except Exception:  # noqa: BLE001 - lỗi ở một detector không được chặn cả phân tích
            logger.exception("Detector %s gặp lỗi", detector_class.name)
    issues.sort(key=lambda i: (_SEVERITY_ORDER.get(i.severity, 3), -len(i.affected_row_indices)))
    return issues
