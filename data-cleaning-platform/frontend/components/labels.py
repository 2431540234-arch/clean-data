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
