"""Sinh báo cáo chất lượng dữ liệu (dùng khi export kèm báo cáo, hoặc xem trên dashboard)."""

import pandas as pd

from app.models.quality_report import QualityReport
from app.schemas.issue import DataIssueOut

_SEVERITY_LABELS = {"high": "Cao", "medium": "Trung bình", "low": "Thấp"}
_TYPE_LABELS = {
    "duplicate": "Trùng lặp",
    "missing": "Thiếu dữ liệu",
    "outlier": "Giá trị bất thường",
    "invalid_format": "Sai định dạng",
    "type_mismatch": "Sai kiểu dữ liệu",
    "inconsistent": "Không nhất quán",
}


def build_quality_report_dataframe(report: QualityReport) -> pd.DataFrame:
    """Bảng chỉ tiêu - giá trị của báo cáo chất lượng (sheet "Báo cáo chất lượng")."""
    summary = report.issue_summary or {}
    rows = [
        ("Điểm chất lượng (0-100)", report.overall_score),
        ("Đầy đủ (0-1)", report.completeness),
        ("Không trùng lặp (0-1)", report.uniqueness),
        ("Hợp lệ (0-1)", report.validity),
        ("Nhất quán (0-1)", report.consistency),
        ("Số dòng", summary.get("rows")),
        ("Số cột", summary.get("columns")),
        ("Ô bị thiếu", summary.get("missing_cells")),
        ("Dòng trùng lặp", summary.get("duplicate_rows")),
        ("Giá trị không hợp lệ", summary.get("invalid_values")),
        ("Giá trị không nhất quán", summary.get("inconsistent_values")),
    ]
    return pd.DataFrame(rows, columns=["Chỉ tiêu", "Giá trị"])


def build_issues_dataframe(issues: list[DataIssueOut]) -> pd.DataFrame:
    """Bảng lỗi đã phát hiện (sheet "Lỗi đã phát hiện")."""
    return pd.DataFrame(
        [
            (
                i.column_name or "(cả bảng)",
                _TYPE_LABELS.get(i.issue_type, i.issue_type),
                _SEVERITY_LABELS.get(i.severity, i.severity),
                i.affected_count,
                i.message,
            )
            for i in issues
        ],
        columns=["Cột", "Loại lỗi", "Mức độ", "Số dòng", "Mô tả"],
    )
