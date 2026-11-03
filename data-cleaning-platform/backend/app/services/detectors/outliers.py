"""Detector phát hiện outlier và giá trị sai kiểu trên các cột số (IQR)."""

import pandas as pd

from app.services.detectors.base import (
    BaseDetector,
    DetectionIssue,
    first_examples,
    severity_by_ratio,
)
from app.services.profiling.values import format_number, null_mask, percent, to_number

MIN_VALUES = 8  # ít hơn thì thống kê tứ phân vị không đáng tin
IQR_FACTOR = 1.5  # ngoài [Q1 - 1,5*IQR, Q3 + 1,5*IQR] là outlier
IQR_FACTOR_EXTREME = 3.0  # ngoài hệ số này là outlier rất xa


class OutliersDetector(BaseDetector):
    """Phát hiện giá trị bất thường (outlier) và giá trị không phải số trên cột số."""

    name = "outliers"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Với mỗi cột số: giá trị không phải số -> type_mismatch; ngoài ngưỡng IQR -> outlier."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] not in ("integer", "float"):
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str).str.strip()
            numbers = present.map(to_number)
            bad = present[numbers.isna()]
            if len(bad):
                issues.append(
                    DetectionIssue(
                        issue_type="type_mismatch",
                        column=str(column),
                        severity=severity_by_ratio(len(bad) / len(present), high=0.1, medium=0.02),
                        message=(
                            f"Cột số '{column}' có {len(bad)} giá trị không phải số "
                            f"(vd. {', '.join(repr(x) for x in first_examples(bad, 3))})."
                        ),
                        affected_row_indices=[int(i) for i in bad.index],
                        extra={"kind": "non_numeric_in_numeric", "examples": first_examples(bad)},
                    )
                )
            valid = numbers.dropna()
            issue = self._outliers(str(column), valid, present)
            if issue:
                issues.append(issue)
        return issues

    @staticmethod
    def _outliers(column: str, valid: pd.Series, present: pd.Series) -> DetectionIssue | None:
        if len(valid) < MIN_VALUES:
            return None
        q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return None
        low, high = q1 - IQR_FACTOR * iqr, q3 + IQR_FACTOR * iqr
        mask = (valid < low) | (valid > high)
        count = int(mask.sum())
        if count == 0:
            return None
        extreme = bool(
            (
                (valid < q1 - IQR_FACTOR_EXTREME * iqr) | (valid > q3 + IQR_FACTOR_EXTREME * iqr)
            ).any()
        )
        outliers = valid[mask]
        return DetectionIssue(
            issue_type="outlier",
            column=column,
            severity="high" if extreme else "medium",
            message=(
                f"Cột '{column}' có {count} giá trị bất thường ({percent(count, len(valid))}), "
                f"ngoài khoảng [{format_number(float(low))}; {format_number(float(high))}]."
            ),
            affected_row_indices=[int(i) for i in outliers.index],
            extra={
                "kind": "iqr_outlier",
                "lower_bound": float(low),
                "upper_bound": float(high),
                "examples": first_examples(present[outliers.index]),
            },
        )
