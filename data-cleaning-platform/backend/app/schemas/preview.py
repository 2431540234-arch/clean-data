"""Schema cho kết quả xem trước (preview) trước/sau khi áp dụng rule."""

from typing import Any

from pydantic import BaseModel

from app.schemas.rule import RuleSet


class PreviewRequest(BaseModel):
    """Yêu cầu xem trước thay đổi khi áp dụng một RuleSet lên một phiên bản dataset."""

    version_id: int
    rule_set: RuleSet
    sample_rows: int = 50


class ColumnDiff(BaseModel):
    """Khác biệt của một cột tại một dòng cụ thể giữa trước và sau khi áp dụng rule."""

    row_index: int
    column: str
    before: Any
    after: Any


class PreviewResult(BaseModel):
    """Kết quả preview: dữ liệu trước/sau trên mẫu dòng, cùng số dòng bị ảnh hưởng."""

    version_id: int
    before_rows: list[dict[str, Any]]
    after_rows: list[dict[str, Any]]
    diffs: list[ColumnDiff]
    affected_row_count: int
