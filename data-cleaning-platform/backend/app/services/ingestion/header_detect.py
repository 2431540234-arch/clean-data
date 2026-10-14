"""Tìm dòng tiêu đề thật trong file Excel/CSV (nhiều file xuất báo cáo có vài dòng rác ở đầu)."""

import pandas as pd


def detect_header_row(raw_df: pd.DataFrame, max_rows_to_check: int = 10) -> int:
    """Trả về chỉ số dòng (0-based) khả năng cao nhất là dòng tiêu đề thật.

    Args:
        raw_df: DataFrame đọc thô, không có header (header=None).
        max_rows_to_check: chỉ xét trong N dòng đầu để tránh quét toàn file.

    Gợi ý cách làm: dòng tiêu đề thường có tỉ lệ cell kiểu chuỗi cao nhất và ít
    giá trị trống nhất so với các dòng dữ liệu phía dưới.
    """
    raise NotImplementedError(
        "TODO: so sánh tỉ lệ ô là chuỗi / ô trống giữa các dòng đầu để suy ra header row."
    )
