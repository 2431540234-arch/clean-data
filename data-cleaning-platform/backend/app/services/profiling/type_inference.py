"""Suy luận kiểu dữ liệu thực tế của một cột (toàn bộ dữ liệu đọc vào là str)."""

import pandas as pd

# Các kiểu dữ liệu suy luận được hỗ trợ.
INFERRED_TYPES = ("integer", "float", "date", "phone", "email", "boolean", "text")


def infer_column_type(series: pd.Series) -> str:
    """Suy luận kiểu dữ liệu của một cột dựa trên mẫu giá trị không rỗng.

    Trả về một trong INFERRED_TYPES.

    Gợi ý cách làm: lấy mẫu các giá trị non-null, thử match theo thứ tự ưu tiên
    email -> phone -> date -> integer -> float -> boolean -> text (dùng regex /
    phonenumbers / dateutil cho từng kiểu, tính tỉ lệ match >= ngưỡng ví dụ 0.8).
    """
    raise NotImplementedError(
        "TODO: thử match mẫu giá trị theo từng kiểu trong INFERRED_TYPES theo thứ tự ưu tiên."
    )
