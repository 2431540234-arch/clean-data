"""Tính diff trước/sau khi áp dụng rule, dùng cho chức năng xem trước (preview)."""

from app.schemas.preview import PreviewResult
from app.schemas.rule import RuleSet


def compute_preview(version_id: int, rule_set: RuleSet, sample_rows: int = 50) -> PreviewResult:
    """Chạy dry_run rule_set trên một mẫu dữ liệu, trả về PreviewResult có diff từng ô.

    Gợi ý cách làm:
    1. Đọc DataFrame của version_id, lấy sample_rows dòng đầu.
    2. Gọi app.services.rules.engine.dry_run.
    3. So sánh từng ô before/after, sinh ColumnDiff cho các ô khác nhau.
    """
    raise NotImplementedError("TODO: dry_run rule trên mẫu dữ liệu và tính diff từng ô.")
