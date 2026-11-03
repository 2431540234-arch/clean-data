"""Detector phát hiện số điện thoại không hợp lệ hoặc nhiều kiểu định dạng (số điện thoại VN)."""

from collections import Counter

import pandas as pd

from app.services.detectors.base import (
    BaseDetector,
    DetectionIssue,
    first_examples,
    severity_by_ratio,
)
from app.services.profiling.values import is_valid_phone, map_unique, null_mask, phone_shape


class PhonesDetector(BaseDetector):
    """Phát hiện cột số điện thoại có giá trị không hợp lệ hoặc không đồng nhất định dạng."""

    name = "phones"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Số không hợp lệ -> invalid_format; hợp lệ nhưng viết nhiều kiểu -> inconsistent."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] != "phone":
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str)
            valid = map_unique(present, is_valid_phone).astype(bool)
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
                            f"Cột '{column}' có {len(invalid)} số điện thoại không hợp lệ "
                            f"(vd. {', '.join(repr(x) for x in first_examples(invalid, 3))})."
                        ),
                        affected_row_indices=[int(i) for i in invalid.index],
                        extra={"kind": "invalid_phone", "examples": first_examples(invalid)},
                    )
                )
            shapes = map_unique(present[valid], phone_shape)
            counts = Counter(shapes)
            if len(counts) > 1:
                dominant = counts.most_common(1)[0][0]
                minority = shapes[shapes != dominant]
                summary = ", ".join(f"{name} ({n} dòng)" for name, n in counts.most_common())
                issues.append(
                    DetectionIssue(
                        issue_type="inconsistent",
                        column=str(column),
                        severity="medium",
                        message=f"Cột '{column}' viết số điện thoại theo nhiều kiểu: {summary}.",
                        affected_row_indices=[int(i) for i in minority.index],
                        extra={
                            "kind": "mixed_phone_format",
                            "shapes": {k: int(n) for k, n in counts.items()},
                            "examples": first_examples(present[minority.index]),
                        },
                    )
                )
        return issues
