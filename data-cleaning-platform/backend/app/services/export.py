"""Xuất dữ liệu đã làm sạch ra CSV (UTF-8-BOM) hoặc Excel (nhiều sheet)."""

import pandas as pd


def export_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Xuất DataFrame ra bytes CSV với encoding UTF-8-BOM (để Excel tiếng Việt mở không lỗi font).

    Gợi ý cách làm: df.to_csv(index=False, encoding="utf-8-sig") ghi vào io.StringIO/BytesIO.
    """
    raise NotImplementedError("TODO: xuất CSV với encoding utf-8-sig.")


def export_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Xuất nhiều DataFrame ra một file Excel nhiều sheet.

    Args:
        sheets: mapping tên sheet -> DataFrame, ví dụ {"Du lieu": df, "Bao cao": report_df}.

    Gợi ý cách làm: dùng pandas.ExcelWriter(io.BytesIO(), engine="openpyxl").
    """
    raise NotImplementedError("TODO: xuất nhiều sheet Excel bằng pandas.ExcelWriter.")
