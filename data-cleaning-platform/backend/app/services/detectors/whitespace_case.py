"""Detector phát hiện khoảng trắng dư và chữ hoa/thường không nhất quán trong cột văn bản."""

import re

import pandas as pd

from app.services.detectors.base import (
    BaseDetector,
    DetectionIssue,
    first_examples,
    severity_by_ratio,
)
from app.services.profiling.values import map_unique, null_mask, percent

_UNTIDY_SPACE_RE = re.compile(r"^\s|\s$|[ \t ]{2,}")
MAX_AVG_LENGTH_FOR_CASE = 40  # cột văn bản dài (ghi chú) thì hoa/thường không có ý nghĩa
_STYLE_LABELS = {"upper": "IN HOA", "lower": "chữ thường", "title": "Viết Hoa Đầu Từ"}


def _case_style(value: str) -> str:
    """'upper' | 'lower' | 'title' | 'other' cho một giá trị văn bản."""
    text = value.strip()
    if not any(ch.isalpha() for ch in text):
        return "other"
    if text.isupper():
        # Từ viết tắt ngắn (HCM, HN, VIP) là hợp lệ khi viết hoa: không tính là "kiểu IN HOA".
        return "upper" if len(text) > 4 else "other"
    if text.islower():
        return "lower"
    words = [w for w in text.split() if any(ch.isalpha() for ch in w)]
    if words and all(w[0].isupper() and not w[1:].isupper() for w in words):
        return "title"
    return "other"


class WhitespaceCaseDetector(BaseDetector):
    """Phát hiện giá trị văn bản có khoảng trắng đầu/cuối/giữa dư hoặc hoa/thường lẫn lộn."""

    name = "whitespace_case"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Khoảng trắng dư (mọi cột trừ email/SĐT, đã có detector riêng) và hoa/thường lẫn lộn."""
        types = self.types_of(df, column_types)
        issues = []
        for column in df.columns:
            if types[column] in ("email", "phone"):
                continue
            series = df[column]
            present = series[~null_mask(series)].astype(str)
            if present.empty:
                continue
            untidy = present[present.str.contains(_UNTIDY_SPACE_RE)]
            if len(untidy):
                issues.append(
                    DetectionIssue(
                        issue_type="inconsistent",
                        column=str(column),
                        severity=severity_by_ratio(
                            len(untidy) / len(present), high=0.3, medium=0.1
                        ),
                        message=(
                            f"Cột '{column}' có {len(untidy)} giá trị thừa khoảng trắng "
                            f"({percent(len(untidy), len(present))})."
                        ),
                        affected_row_indices=[int(i) for i in untidy.index],
                        extra={"kind": "extra_whitespace", "examples": first_examples(untidy)},
                    )
                )
            if types[column] == "text":
                issue = self._mixed_case(str(column), present)
                if issue:
                    issues.append(issue)
        return issues

    @staticmethod
    def _mixed_case(column: str, present: pd.Series) -> DetectionIssue | None:
        if present.str.len().mean() > MAX_AVG_LENGTH_FOR_CASE:
            return None
        styles = map_unique(present, _case_style)
        counts = styles[styles != "other"].value_counts()
        if len(counts) < 2:
            return None
        dominant = counts.index[0]
        minimum = max(2, int(0.05 * len(present)))
        minority_counts = counts.drop(dominant)
        if (minority_counts < minimum).all():
            return None
        minority = present[styles.isin(minority_counts.index) & (styles != dominant)]
        summary = ", ".join(f"{n} giá trị {_STYLE_LABELS[s]}" for s, n in counts.items())
        return DetectionIssue(
            issue_type="inconsistent",
            column=column,
            severity="low" if len(minority) / len(present) < 0.2 else "medium",
            message=f"Cột '{column}' viết hoa/thường không thống nhất: {summary}.",
            affected_row_indices=[int(i) for i in minority.index],
            extra={
                "kind": "mixed_case",
                "dominant_style": dominant,
                "styles": {k: int(n) for k, n in counts.items()},
                "examples": first_examples(minority),
            },
        )
