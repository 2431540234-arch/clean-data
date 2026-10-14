"""Import toàn bộ module op để chúng tự đăng ký vào registry (app.services.rules.registry.OPS)."""

from app.services.rules.ops import (
    column_ops,
    contact_ops,
    date_ops,
    missing_ops,
    outlier_ops,
    row_ops,
    text_ops,
    type_ops,
)

__all__ = [
    "text_ops",
    "date_ops",
    "contact_ops",
    "type_ops",
    "missing_ops",
    "row_ops",
    "outlier_ops",
    "column_ops",
]
