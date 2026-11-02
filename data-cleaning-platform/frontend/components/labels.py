"""Nhãn tiếng Việt cho các giá trị kỹ thuật trả về từ backend."""

# Khớp INFERRED_TYPES của backend/app/services/profiling/type_inference.py.
TYPE_LABELS = {
    "integer": "Số nguyên",
    "float": "Số thực",
    "date": "Ngày",
    "phone": "Điện thoại",
    "email": "Email",
    "boolean": "Đúng/Sai",
    "text": "Văn bản",
}


def type_label(inferred_type: str) -> str:
    """Nhãn tiếng Việt của kiểu dữ liệu suy luận; kiểu lạ giữ nguyên."""
    return TYPE_LABELS.get(inferred_type, inferred_type)


# Khớp ALLOWED_OPS của backend/app/schemas/rule.py.
OP_LABELS = {
    "trim_whitespace": "Cắt khoảng trắng thừa",
    "change_case": "Đổi chữ hoa/thường",
    "replace_values": "Thay thế giá trị",
    "standardize_date": "Chuẩn hóa ngày",
    "standardize_phone": "Chuẩn hóa số điện thoại",
    "standardize_email": "Chuẩn hóa email",
    "cast_type": "Ép kiểu dữ liệu",
    "fill_missing": "Điền giá trị thiếu",
    "drop_duplicates": "Xóa dòng trùng lặp",
    "drop_rows_where": "Xóa dòng theo điều kiện",
    "flag_outliers": "Đánh dấu giá trị bất thường",
    "rename_column": "Đổi tên cột",
    "drop_column": "Xóa cột",
}

# Khớp SuggestionOut.status / source.
STATUS_LABELS = {"pending": "Chưa duyệt", "accepted": "Đã chấp nhận", "rejected": "Đã từ chối"}
SOURCE_LABELS = {"ai": "AI đề xuất", "rule_engine": "Quy tắc"}


def op_label(op: str) -> str:
    """Nhãn tiếng Việt của một op rule; op lạ giữ nguyên."""
    return OP_LABELS.get(op, op)


def describe_step(step: dict) -> str:
    """Mô tả ngắn một RuleStep cho người dùng, ví dụ: Chuẩn hóa ngày — cột “ngay_sinh”."""
    op, column = step["op"], step.get("column")
    if op == "rename_column":
        new_name = (step.get("params") or {}).get("new_name", "?")
        return f"Đổi tên cột “{column}” thành “{new_name}”"
    label = op_label(op)
    return f"{label} — cột “{column}”" if column else f"{label} (toàn bộ bảng)"
