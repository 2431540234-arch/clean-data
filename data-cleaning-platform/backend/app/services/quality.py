"""Tính Data Quality Score cho một phiên bản dataset (công thức chi tiết: docs/quality_score.md)."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from app.services.detectors import run_all_detectors
from app.services.detectors.base import DetectionIssue
from app.services.profiling.type_inference import infer_column_type
from app.services.profiling.values import null_mask

# Trọng số các tiêu chí tính điểm chất lượng, xem chi tiết công thức ở docs/quality_score.md.
QUALITY_WEIGHTS = {
    "completeness": 0.3,
    "uniqueness": 0.2,
    "validity": 0.3,
    "consistency": 0.2,
}

# Loại lỗi (mã `kind` của detector) tính vào từng tiêu chí.
VALIDITY_KINDS = {
    "invalid_email",
    "invalid_phone",
    "invalid_date",
    "non_numeric_in_numeric",
    "iqr_outlier",
}
CONSISTENCY_KINDS = {
    "mixed_date_format",
    "mixed_phone_format",
    "email_case_whitespace",
    "extra_whitespace",
    "mixed_case",
    "value_variants",
}
VALIDITY_TYPES = {"email", "phone", "date", "integer", "float"}  # cột có định dạng để kiểm tra
CONSISTENCY_TYPES = {"text", "email", "phone", "date"}  # cột có thể viết nhiều kiểu


@dataclass
class QualityMetrics:
    """Kết quả tính điểm: overall 0..100, bốn tiêu chí thành phần 0..1, và bảng đếm."""

    overall_score: float
    completeness: float
    uniqueness: float
    validity: float
    consistency: float
    issue_summary: dict[str, Any] = field(default_factory=dict)


def _ratio_ok(bad: int, total: int) -> float:
    """1 - bad/total, kẹp trong [0, 1]; không có gì để kiểm tra thì coi là tốt (1.0)."""
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, 1 - bad / total))


def compute_quality_score(
    df: pd.DataFrame,
    issues: list[DetectionIssue] | None = None,
    column_types: dict[str, str] | None = None,
) -> QualityMetrics:
    """Tính điểm chất lượng tổng hợp (0-100) dựa trên completeness/uniqueness/validity/consistency.

    issues / column_types: kết quả detector và kiểu cột nếu đã có (khỏi tính lại);
    thiếu thì tự tính.
    """
    types = dict(column_types or {})
    for column in df.columns:
        types.setdefault(column, infer_column_type(df[column]))
    found = issues if issues is not None else run_all_detectors(df, types)

    rows, cols = len(df), len(df.columns)
    null_masks = {c: null_mask(df[c]) for c in df.columns}
    missing_cells = int(sum(m.sum() for m in null_masks.values()))
    filled = {c: rows - int(m.sum()) for c, m in null_masks.items()}

    duplicate_rows = sum(
        len(i.affected_row_indices) for i in found if i.extra.get("kind") == "exact_duplicate_rows"
    )
    invalid_cells = _cells(found, VALIDITY_KINDS)
    inconsistent_cells = _cells(found, CONSISTENCY_KINDS)

    validity_total = sum(filled[c] for c in df.columns if types[c] in VALIDITY_TYPES)
    consistency_total = sum(filled[c] for c in df.columns if types[c] in CONSISTENCY_TYPES)

    components = {
        "completeness": _ratio_ok(missing_cells, rows * cols),
        "uniqueness": _ratio_ok(duplicate_rows, rows),
        "validity": _ratio_ok(len(invalid_cells), validity_total),
        "consistency": _ratio_ok(len(inconsistent_cells), consistency_total),
    }
    overall = 100 * sum(QUALITY_WEIGHTS[name] * value for name, value in components.items())
    return QualityMetrics(
        overall_score=round(overall, 1),
        issue_summary={
            "rows": rows,
            "columns": cols,
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "invalid_values": len(invalid_cells),
            "inconsistent_values": len(inconsistent_cells),
            "issue_count": len(found),
            "high_severity": sum(1 for i in found if i.severity == "high"),
        },
        **{name: round(value, 4) for name, value in components.items()},
    )


def _cells(issues: list[DetectionIssue], kinds: set[str]) -> set[tuple[str | None, int]]:
    """Tập ô (cột, dòng) bị lỗi thuộc các loại `kinds`; ô lỗi nhiều kiểu chỉ đếm một lần."""
    cells: set[tuple[str | None, int]] = set()
    for issue in issues:
        if issue.extra.get("kind") in kinds:
            cells.update((issue.column, row) for row in issue.affected_row_indices)
    return cells
