"""Kiểm tra DSL rule phía giao diện trước khi lưu hoặc đưa vào hàng đợi."""

from typing import Any

from components.rule_catalog import SUPPORTED_RULE_OPS

_COLUMN_OPTIONAL_OPS = {"drop_duplicates"}
_DROP_ROW_OPERATORS = {"gt", "lt", "gte", "lte", "eq", "neq", "is_null", "is_not_null"}


def validate_rule_set(
    rule_set: dict[str, Any], available_columns: list[str] | None = None
) -> tuple[bool, list[str]]:
    """Trả trạng thái hợp lệ và lỗi cấu trúc/cột theo DSL."""
    steps = rule_set.get("steps") if isinstance(rule_set, dict) else None
    if not isinstance(steps, list) or not steps:
        return False, ["Quy tắc phải có ít nhất 1 bước xử lý."]

    errors = []
    for index, step in enumerate(steps, start=1):
        prefix = f"Bước {index}"
        if not isinstance(step, dict):
            errors.append(f"{prefix}: Cấu trúc không phải đối tượng JSON hợp lệ.")
            continue

        op = step.get("op")
        if op not in SUPPORTED_RULE_OPS:
            errors.append(f"{prefix}: Phép biến đổi '{op}' không được hỗ trợ.")
            continue

        column = step.get("column")
        if op not in _COLUMN_OPTIONAL_OPS and (not isinstance(column, str) or not column.strip()):
            errors.append(f"{prefix} ({op}): Bắt buộc phải chỉ định tên cột.")
        elif available_columns is not None and column and column not in available_columns:
            errors.append(f"{prefix}: Cột '{column}' không tồn tại trong dataset hiện tại.")

        params = step.get("params", {})
        if not isinstance(params, dict):
            errors.append(f"{prefix}: 'params' phải là một đối tượng JSON.")
            continue
        if op == "rename_column" and not str(params.get("new_name", "")).strip():
            errors.append(f"{prefix}: Bắt buộc phải nhập tên cột mới.")
        if op == "drop_rows_where":
            operator = params.get("operator")
            if operator not in _DROP_ROW_OPERATORS:
                errors.append(f"{prefix}: Điều kiện xóa dòng không hợp lệ.")
            elif operator not in {"is_null", "is_not_null"} and params.get("value") is None:
                errors.append(f"{prefix}: Điều kiện này cần có giá trị so sánh.")

    return not errors, errors
