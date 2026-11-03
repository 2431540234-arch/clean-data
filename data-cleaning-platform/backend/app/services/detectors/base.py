"""Lớp Detector chung: mọi detector lỗi dữ liệu kế thừa từ đây."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.services.profiling.type_inference import infer_column_type

EXAMPLE_LIMIT = 5


@dataclass
class DetectionIssue:
    """Một vấn đề dữ liệu được phát hiện trên một hoặc nhiều dòng của một cột.

    issue_type thuộc: duplicate | missing | outlier | invalid_format | type_mismatch | inconsistent.
    extra["kind"] là mã chi tiết (vd. "mixed_date_format") để bước sinh gợi ý biết cách sửa;
    extra["examples"] là vài giá trị mẫu hiển thị cho người dùng.
    """

    issue_type: str
    column: str | None
    severity: str
    message: str
    affected_row_indices: list[int] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


def severity_by_ratio(ratio: float, high: float, medium: float) -> str:
    """Mức nghiêm trọng theo tỉ lệ dòng bị ảnh hưởng."""
    if ratio >= high:
        return "high"
    if ratio >= medium:
        return "medium"
    return "low"


def first_examples(values: pd.Series, limit: int = EXAMPLE_LIMIT) -> list[str]:
    """Vài giá trị khác nhau đầu tiên (giữ nguyên khoảng trắng thật để người dùng thấy lỗi)."""
    return [str(x) for x in values.drop_duplicates().head(limit)]


class BaseDetector(ABC):
    """Interface chung cho mọi detector: nhận DataFrame, trả về danh sách DetectionIssue."""

    name: str = "base"

    @abstractmethod
    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Phát hiện lỗi trên df và trả về danh sách DetectionIssue.

        column_types (tên cột -> kiểu suy luận) có thể truyền sẵn để khỏi suy luận lại.
        """
        raise NotImplementedError

    @staticmethod
    def types_of(df: pd.DataFrame, column_types: dict[str, str] | None) -> dict[str, str]:
        """Kiểu của từng cột: dùng bản truyền vào, thiếu cột nào thì suy luận cột đó."""
        known = dict(column_types or {})
        for column in df.columns:
            if column not in known:
                known[column] = infer_column_type(df[column])
        return known
