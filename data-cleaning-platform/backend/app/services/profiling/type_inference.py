"""Suy luận kiểu dữ liệu thực tế của một cột (toàn bộ dữ liệu đọc vào là str)."""

from collections.abc import Callable

import pandas as pd

from app.services.profiling import values as v

# Các kiểu dữ liệu suy luận được hỗ trợ.
INFERRED_TYPES = ("integer", "float", "date", "phone", "email", "boolean", "text")

MATCH_THRESHOLD = 0.8  # tỉ lệ giá trị khớp tối thiểu để kết luận kiểu của cột
SAMPLE_LIMIT = 5000  # cột dài chỉ xét mẫu cố định để suy luận nhanh và lặp lại được

# Thứ tự ưu tiên: email -> phone -> date -> integer -> float -> boolean -> text.
_CHECKS: list[tuple[str, Callable[[str], bool]]] = [
    ("email", v.is_email),
    ("phone", v.looks_like_phone),
    ("date", lambda value: v.date_format_of(value) is not None),
    ("integer", v.is_integer),
    ("float", v.is_number),
    ("boolean", v.is_boolean),
]


def infer_column_type(series: pd.Series) -> str:
    """Suy luận kiểu dữ liệu của một cột dựa trên các giá trị không rỗng.

    Trả về một trong INFERRED_TYPES. Một kiểu được chọn khi >= 80% giá trị không rỗng khớp nó
    (nhờ vậy vài giá trị bẩn như "N/A" hay "abc" không làm cột số bị coi là text).
    """
    values = v.non_null_values(series)
    if values.empty:
        return "text"
    if len(values) > SAMPLE_LIMIT:
        values = values.sample(SAMPLE_LIMIT, random_state=0)
    counts = values.value_counts()
    total = int(counts.sum())
    for name, predicate in _CHECKS:
        matched = sum(int(count) for value, count in counts.items() if predicate(value))
        if matched / total >= MATCH_THRESHOLD:
            return name
    return "text"
