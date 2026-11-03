"""Detector phát hiện dữ liệu thiếu (null, chuỗi rỗng, các token coi như null)."""

import pandas as pd

from app.services.detectors.base import BaseDetector, DetectionIssue, severity_by_ratio
from app.services.profiling.values import null_mask, percent


class MissingDetector(BaseDetector):
    """Phát hiện các cột có dữ liệu thiếu, dựa trên app/data/null_tokens.json."""

    name = "missing"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Một DetectionIssue cho mỗi cột có ô thiếu; severity tăng theo tỉ lệ thiếu."""
        issues = []
        total = len(df)
        for column in df.columns:
            mask = null_mask(df[column])
            count = int(mask.sum())
            if count == 0:
                continue
            ratio = count / total
            tokens = df[column][mask].astype(str).str.strip().replace("", "(ô trống)")
            token_counts = tokens.value_counts().head(5)
            issues.append(
                DetectionIssue(
                    issue_type="missing",
                    column=str(column),
                    severity=severity_by_ratio(ratio, high=0.5, medium=0.2),
                    message=(
                        f"Cột '{column}' thiếu {count}/{total} giá trị ({percent(count, total)})."
                    ),
                    affected_row_indices=[int(i) for i in df.index[mask]],
                    extra={
                        "kind": "missing_values",
                        "ratio": round(ratio, 4),
                        "examples": [str(t) for t in token_counts.index],
                        "tokens": {str(k): int(c) for k, c in token_counts.items()},
                    },
                )
            )
        return issues
