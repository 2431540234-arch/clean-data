"""Tính diff trước/sau khi áp dụng rule, dùng cho chức năng xem trước (preview)."""

from typing import Any

import pandas as pd

from app.core.exceptions import ValidationAppError
from app.models.dataset import DatasetVersion
from app.schemas.preview import ColumnDiff, PreviewResult
from app.schemas.rule import RuleSet
from app.services.frames import load_version_frame
from app.services.rules.engine import changed_row_labels, dry_run
from app.services.rules.registry import RuleError

MIN_SAMPLE_ROWS = 1
MAX_SAMPLE_ROWS = 500
# Tới ngưỡng này mới chạy thử trên TOÀN BỘ dữ liệu để đếm đúng số dòng bị ảnh hưởng; lớn hơn thì
# chỉ dùng mẫu để preview luôn nhanh.
FULL_COUNT_MAX_ROWS = 200_000


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(k): ("" if v is None or v != v else str(v)) for k, v in row.items()}
        for row in frame.to_dict("records")
    ]


def compute_preview(
    version: DatasetVersion, rule_set: RuleSet, sample_rows: int = 50
) -> PreviewResult:
    """Chạy dry_run rule_set trên mẫu dữ liệu, trả về PreviewResult có diff từng ô.

    - before_rows / after_rows: `sample_rows` dòng đầu (1..500) trước/sau, giữ nguyên thứ tự dòng
      (dòng bị xóa chỉ biến mất ở after_rows). Mọi giá trị là chuỗi, ô thiếu là "".
    - diffs: chỉ các ô đổi giá trị ở cột có cả trước và sau; row_index là vị trí 0-based trong
      before_rows.
    - affected_row_count: đếm trên toàn bộ dữ liệu khi bảng không quá lớn, ngược lại trên mẫu.
    """
    sample_rows = max(MIN_SAMPLE_ROWS, min(int(sample_rows), MAX_SAMPLE_ROWS))
    frame = load_version_frame(version)
    sample = frame.head(sample_rows)
    try:
        after, _ = dry_run(sample, rule_set)
        if len(frame) <= FULL_COUNT_MAX_ROWS:
            full_after, _ = dry_run(frame, rule_set)  # cũng báo sớm lỗi chỉ xuất hiện ngoài mẫu
            affected = len(changed_row_labels(frame, full_after))
        else:
            affected = len(changed_row_labels(sample, after))
    except RuleError as exc:
        raise ValidationAppError(str(exc)) from exc

    diffs: list[ColumnDiff] = []
    shared = [c for c in sample.columns if c in after.columns]
    for position, label in enumerate(sample.index):
        if label not in after.index:
            continue
        for column in shared:
            before_value, after_value = sample.at[label, column], after.at[label, column]
            if str(before_value) != str(after_value):
                diffs.append(
                    ColumnDiff(
                        row_index=position,
                        column=str(column),
                        before=before_value,
                        after=after_value,
                    )
                )
    return PreviewResult(
        version_id=version.id,
        before_rows=_records(sample),
        after_rows=_records(after),
        diffs=diffs,
        affected_row_count=affected,
    )
