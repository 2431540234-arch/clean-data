"""Xuất dữ liệu đã làm sạch ra CSV (UTF-8-BOM) hoặc Excel (nhiều sheet).

Chống "CSV/formula injection": ô văn bản bắt đầu bằng = + - @ (hoặc tab/CR) bị Excel/Google
Sheets hiểu là công thức khi mở file. CSV: thêm dấu nháy đơn ở đầu các ô đó (trừ ô là số như -5
hay +84901234567). Excel: ghi mọi ô văn bản là chuỗi, không bao giờ là công thức.
"""

import io

import pandas as pd

from app.core.exceptions import ValidationAppError
from app.services.profiling.values import is_number

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_MAX_SHEET_NAME = 31
# Một sheet Excel có 1.048.576 dòng, trừ 1 dòng tiêu đề. Vượt thì từ chối, không tự cắt dữ liệu.
EXCEL_MAX_DATA_ROWS = 1_048_575


def _neutralize(value: object) -> object:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES) and not is_number(value):
        return "'" + value
    return value


def neutralize_formulas(df: pd.DataFrame) -> pd.DataFrame:
    """Bản sao của df đã thêm dấu nháy trước các ô có thể bị hiểu là công thức (cả tên cột)."""
    safe = df.copy()
    for column in safe.columns:
        safe[column] = safe[column].map(_neutralize)
    safe.columns = [_neutralize(str(c)) for c in safe.columns]
    return safe


def ensure_fits_excel(sheet_name: str, data_rows: int) -> None:
    """Từ chối nếu `data_rows` dòng dữ liệu không vừa một sheet Excel; gợi ý xuất CSV."""
    if data_rows > EXCEL_MAX_DATA_ROWS:
        shown = f"{data_rows:,}".replace(",", ".")
        limit = f"{EXCEL_MAX_DATA_ROWS:,}".replace(",", ".")
        raise ValidationAppError(
            f"Sheet “{sheet_name}” có {shown} dòng, vượt giới hạn {limit} dòng dữ liệu của Excel. "
            "Hãy xuất CSV để lấy đủ dữ liệu (CSV không giới hạn số dòng)."
        )


def export_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Xuất DataFrame ra bytes CSV UTF-8-BOM (để Excel tiếng Việt mở không lỗi font)."""
    buffer = io.StringIO()
    neutralize_formulas(df).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8-sig")


def export_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Xuất nhiều DataFrame ra một file Excel nhiều sheet (ô văn bản luôn là chuỗi).

    Args:
        sheets: mapping tên sheet -> DataFrame, ví dụ {"Dữ liệu": df, "Báo cáo chất lượng": report}.
    """
    for name, frame in sheets.items():
        ensure_fits_excel(name, len(frame))
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name[:_MAX_SHEET_NAME], index=False)
        for worksheet in writer.book.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if cell.data_type == "f":  # openpyxl tự coi chuỗi bắt đầu bằng "=" là công thức
                        cell.data_type = "s"
    return buffer.getvalue()
