"""Tìm dòng tiêu đề thật trong file Excel/CSV (nhiều file xuất báo cáo có vài dòng rác ở đầu)."""

import math

import pandas as pd


def detect_header_row(raw_df: pd.DataFrame, max_rows_to_check: int = 10) -> int:
    """Trả về chỉ số dòng (0-based) khả năng cao nhất là dòng tiêu đề thật.

    Args:
        raw_df: DataFrame đọc thô, không có header (header=None), ô trống là chuỗi rỗng.
        max_rows_to_check: chỉ xét trong N dòng đầu để tránh quét toàn file.

    Dòng rác ở đầu (tiêu đề báo cáo, dòng trống, ghi chú) thường chỉ có 0-1 ô có chữ, trong khi
    dòng tiêu đề thật có gần đủ số cột như các dòng dữ liệu. Vì vậy dòng tiêu đề là dòng đầu
    tiên có số ô không trống đạt ít nhất 60% độ rộng lớn nhất trong phần đầu file. File không
    có dòng rác sẽ luôn trả về 0.
    """
    rows = min(len(raw_df), max_rows_to_check)
    if rows < 2:
        return 0
    filled = [int((raw_df.iloc[i].astype(str).str.strip() != "").sum()) for i in range(rows)]
    width = max(filled)
    if width < 2:
        return 0
    threshold = max(2, math.ceil(0.6 * width))
    for index, count in enumerate(filled):
        if count >= threshold:
            return index
    return 0
