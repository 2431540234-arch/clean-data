"""Lớp Detector chung: mọi detector lỗi dữ liệu kế thừa từ đây."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class DetectionIssue:
    """Một vấn đề dữ liệu được phát hiện trên một hoặc nhiều dòng của một cột."""

    issue_type: str
    column: str | None
    severity: str
    message: str
    affected_row_indices: list[int] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    """Interface chung cho mọi detector: nhận DataFrame, trả về danh sách DetectionIssue."""

    name: str = "base"

    @abstractmethod
    def detect(self, df: pd.DataFrame) -> list[DetectionIssue]:
        """Phát hiện lỗi trên df và trả về danh sách DetectionIssue.

        Các lớp con (missing, duplicates, outliers, dates, phones, emails,
        whitespace_case, inconsistency) phải implement hàm này.
        """
        raise NotImplementedError("TODO: lớp con phải implement detect().")
