"""Detector phát hiện email không hợp lệ hoặc viết không nhất quán (hoa/thường, khoảng trắng)."""

import pandas as pd

from app.services.detectors.base import (
    BaseDetector,
    DetectionIssue,
    first_examples,
    severity_by_ratio,
)
from app.services.profiling.values import is_email, map_unique, null_mask


class EmailsDetector(BaseDetector):
    """Phát hiện cột email có giá trị không hợp lệ hoặc có khoảng trắng/hoa thường thừa."""

    name = "emails"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Email sai cú pháp -> invalid_format; thừa khoảng trắng/chữ hoa -> inconsistent."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] != "email":
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str)
            valid = map_unique(present, is_email).astype(bool)
            invalid = present[~valid]
            if len(invalid):
                issues.append(
                    DetectionIssue(
                        issue_type="invalid_format",
                        column=str(column),
                        severity=severity_by_ratio(
                            len(invalid) / len(present), high=0.1, medium=0.02
                        ),
                        message=(
                            f"Cột '{column}' có {len(invalid)} email sai cú pháp "
                            f"(vd. {', '.join(repr(x) for x in first_examples(invalid, 3))})."
                        ),
                        affected_row_indices=[int(i) for i in invalid.index],
                        extra={"kind": "invalid_email", "examples": first_examples(invalid)},
                    )
                )
            untidy = present[valid & (present != present.str.strip().str.lower())]
            if len(untidy):
                issues.append(
                    DetectionIssue(
                        issue_type="inconsistent",
                        column=str(column),
                        severity="low" if len(untidy) / len(present) < 0.2 else "medium",
                        message=(
                            f"Cột '{column}' có {len(untidy)} email thừa khoảng trắng hoặc viết "
                            f"hoa (vd. {', '.join(repr(x) for x in first_examples(untidy, 3))})."
                        ),
                        affected_row_indices=[int(i) for i in untidy.index],
                        extra={"kind": "email_case_whitespace", "examples": first_examples(untidy)},
                    )
                )
        return issues
