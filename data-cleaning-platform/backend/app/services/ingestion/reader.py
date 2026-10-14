"""Đọc file CSV/Excel thành pandas DataFrame, luôn đọc dtype=str để giữ nguyên dữ liệu gốc."""

from dataclasses import dataclass

import pandas as pd


@dataclass
class ReadResult:
    """Kết quả đọc file: DataFrame và danh sách tên sheet (rỗng nếu là CSV)."""

    dataframe: pd.DataFrame
    sheet_names: list[str]
    used_sheet: str | None


def read_csv_file(file_bytes: bytes, encoding: str, delimiter: str) -> pd.DataFrame:
    """Đọc file CSV thành DataFrame, mọi cột đọc dưới dạng str (dtype=str).

    Gợi ý cách làm: dùng io.BytesIO(file_bytes) + pd.read_csv(..., dtype=str,
    keep_default_na=False, encoding=encoding, sep=delimiter).
    """
    raise NotImplementedError("TODO: đọc CSV bằng pandas với dtype=str, encoding, delimiter.")


def list_excel_sheets(file_bytes: bytes) -> list[str]:
    """Trả về danh sách tên sheet có trong file Excel.

    Gợi ý cách làm: dùng pandas.ExcelFile(io.BytesIO(file_bytes)).sheet_names.
    """
    raise NotImplementedError("TODO: dùng pandas.ExcelFile để lấy danh sách sheet.")


def read_excel_sheet(file_bytes: bytes, sheet_name: str) -> pd.DataFrame:
    """Đọc một sheet cụ thể của file Excel thành DataFrame, mọi cột đọc dưới dạng str.

    Gợi ý cách làm: pd.read_excel(..., sheet_name=sheet_name, dtype=str, engine="openpyxl").
    """
    raise NotImplementedError("TODO: đọc sheet Excel bằng pandas với dtype=str.")


def read_dataset_file(
    file_bytes: bytes, filename: str, sheet_name: str | None = None
) -> ReadResult:
    """Điểm vào chung: nhận diện CSV hay Excel từ phần mở rộng file và đọc thành DataFrame.

    Gợi ý cách làm: nếu filename kết thúc bằng .csv -> dùng detect_encoding + detect_delimiter
    + read_csv_file; nếu .xlsx/.xls -> dùng list_excel_sheets + read_excel_sheet.
    """
    raise NotImplementedError("TODO: phân loại CSV/Excel theo đuôi file và gọi hàm đọc tương ứng.")
