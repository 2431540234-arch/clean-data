"""Detector phát hiện dòng trùng lặp tuyệt đối và trùng lặp gần đúng (fuzzy)."""

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process

from app.services.detectors.base import BaseDetector, DetectionIssue, severity_by_ratio
from app.services.profiling.values import normalize_key, percent

NEAR_DUPLICATE_SCORE = 95  # độ giống tối thiểu (0-100) để coi là trùng gần đúng
NEAR_DUPLICATE_MAX_ROWS = 2000  # ma trận so sánh cặp O(n^2): bỏ qua với bảng lớn hơn
MIN_KEY_LENGTH = 8  # khóa quá ngắn thì giống nhau là chuyện thường, không đáng tin


def _row_preview(row: pd.Series, limit: int = 3) -> str:
    cells = [f"{col}={val}" for col, val in row.items() if str(val).strip()][:limit]
    return "; ".join(cells)


class DuplicatesDetector(BaseDetector):
    """Phát hiện dòng trùng lặp tuyệt đối (df.duplicated()) và gần đúng (rapidfuzz)."""

    name = "duplicates"

    def detect(
        self, df: pd.DataFrame, column_types: dict[str, str] | None = None
    ) -> list[DetectionIssue]:
        """Trả về DetectionIssue cho dòng trùng hoàn toàn và dòng gần như trùng.

        Dòng "bị ảnh hưởng" là các bản sao đứng sau bản đầu tiên (xóa chúng là xong).
        """
        total = len(df)
        if total < 2:
            return []
        issues = []
        exact = df.duplicated(keep="first")
        count = int(exact.sum())
        if count:
            issues.append(
                DetectionIssue(
                    issue_type="duplicate",
                    column=None,
                    severity=severity_by_ratio(count / total, high=0.1, medium=0.02),
                    message=(
                        f"Có {count} dòng trùng hoàn toàn với dòng khác ({percent(count, total)})."
                    ),
                    affected_row_indices=[int(i) for i in df.index[exact]],
                    extra={
                        "kind": "exact_duplicate_rows",
                        "examples": [_row_preview(row) for _, row in df[exact].head(3).iterrows()],
                    },
                )
            )
        near = self._near_duplicates(df[~exact], self.types_of(df, column_types))
        if near:
            issues.append(
                DetectionIssue(
                    issue_type="duplicate",
                    column=None,
                    severity="medium" if len(near) / total >= 0.02 else "low",
                    message=(
                        f"Có {len(near)} dòng gần như trùng với dòng khác "
                        f"(chỉ khác khoảng trắng, hoa/thường, dấu hoặc lỗi gõ nhẹ)."
                    ),
                    affected_row_indices=near,
                    extra={
                        "kind": "near_duplicate_rows",
                        "examples": [_row_preview(df.loc[i]) for i in near[:3]],
                    },
                )
            )
        return issues

    @staticmethod
    def _near_duplicates(df: pd.DataFrame, types: dict[str, str]) -> list[int]:
        """Nhãn dòng là bản sao gần đúng của một dòng đứng trước nó.

        Chỉ so sánh các cột chữ (text/email/SĐT): cột số và ngày thường khác nhau giữa hai bản
        ghi hợp lệ (số tiền, ngày mua) nên đưa vào sẽ gây báo nhầm.
        """
        if len(df) < 2 or len(df) > NEAR_DUPLICATE_MAX_ROWS:
            return []
        keep = [c for c in df.columns if types.get(c) in ("text", "email", "phone")]
        if not keep:
            return []
        keys = []
        for _, row in df[keep].iterrows():
            parts = [normalize_key(str(x)) for x in row if str(x).strip()]
            keys.append(" ".join(parts))
        usable = [i for i, key in enumerate(keys) if len(key) >= MIN_KEY_LENGTH]
        if len(usable) < 2:
            return []
        scores = process.cdist(
            [keys[i] for i in usable],
            [keys[i] for i in usable],
            scorer=fuzz.ratio,
            dtype=np.uint8,
            score_cutoff=NEAR_DUPLICATE_SCORE,
            workers=1,
        )
        labels = list(df.index)
        redundant: set[int] = set()
        for a in range(len(usable)):
            if a in redundant:
                continue
            for b in range(a + 1, len(usable)):
                if scores[a, b] >= NEAR_DUPLICATE_SCORE:
                    redundant.add(b)
        return [int(labels[usable[b]]) for b in sorted(redundant)]
