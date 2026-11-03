"""Detector phát hiện cột ngày tháng bị lẫn nhiều định dạng (dd/mm/yyyy, yyyy-mm-dd...)."""

from collections import Counter

import pandas as pd

from app.services.detectors.base import (
    BaseDetector,
    DetectionIssue,
    first_examples,
    severity_by_ratio,
)
from app.services.profiling.values import map_unique, null_mask, parse_date


class DatesDetector(BaseDetector):
    """Phát hiện cột ngày tháng có nhiều định dạng không thống nhất hoặc không parse được."""

    name = "dates"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Cột ngày: không phải ngày thật -> invalid_format; lẫn định dạng -> inconsistent."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] != "date":
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str).str.strip()
            labels = map_unique(present, lambda value: (parse_date(value) or (None,))[0])
            invalid = present[labels.isna()]
            if len(invalid):
                issues.append(
                    DetectionIssue(
                        issue_type="invalid_format",
                        column=str(column),
                        severity=severity_by_ratio(
                            len(invalid) / len(present), high=0.1, medium=0.02
                        ),
                        message=(
                            f"Cột ngày '{column}' có {len(invalid)} giá trị không phải ngày hợp lệ "
                            f"(vd. {', '.join(repr(x) for x in first_examples(invalid, 3))})."
                        ),
                        affected_row_indices=[int(i) for i in invalid.index],
                        extra={"kind": "invalid_date", "examples": first_examples(invalid)},
                    )
                )
            counts = Counter(labels.dropna())
            if len(counts) > 1:
                dominant = counts.most_common(1)[0][0]
                minority = labels[labels.notna() & (labels != dominant)]
                summary = ", ".join(f"{label} ({n} dòng)" for label, n in counts.most_common())
                issues.append(
                    DetectionIssue(
                        issue_type="inconsistent",
                        column=str(column),
                        severity="medium",
                        message=f"Cột ngày '{column}' lẫn {len(counts)} định dạng: {summary}.",
                        affected_row_indices=[int(i) for i in minority.index],
                        extra={
                            "kind": "mixed_date_format",
                            "formats": {k: int(n) for k, n in counts.items()},
                            "dominant": dominant,
                            "examples": first_examples(present[minority.index]),
                        },
                    )
                )
        return issues
