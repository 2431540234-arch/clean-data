"""Đọc file CSV/Excel thành pandas DataFrame, luôn đọc dtype=str để giữ nguyên dữ liệu gốc."""

import csv
import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass

import pandas as pd
from pandas.errors import EmptyDataError, ParserError

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.services.ingestion.delimiter import detect_delimiter
from app.services.ingestion.encoding import detect_encoding
from app.services.ingestion.header_detect import detect_header_row

# Tổng dung lượng giải nén tối đa của file xlsx (chống "zip bomb").
_MAX_UNZIPPED_BYTES = 500 * 1024 * 1024
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2} 00:00:00$")
_XLS_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_SAMPLE_BYTES = 200_000
_SAMPLE_LINES = 200


@dataclass
class ReadResult:
    """Kết quả đọc file: DataFrame, tên các sheet (rỗng nếu là CSV), sheet và encoding đã dùng."""

    dataframe: pd.DataFrame
    sheet_names: list[str]
    used_sheet: str | None
    encoding: str | None = None


def file_type_from_name(filename: str) -> str:
    """Loại file theo đuôi ('csv' | 'xlsx' | 'xls'); đuôi khác bị từ chối."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ("csv", "xlsx", "xls"):
        raise ValidationAppError("Định dạng file không được hỗ trợ. Chỉ nhận CSV hoặc Excel.")
    return extension


def check_file_signature(file_type: str, content: bytes) -> None:
    """Kiểm tra nội dung thật khớp với đuôi file (không tin tên file do người dùng gửi)."""
    if not content.strip():
        raise ValidationAppError("File không có dữ liệu.")
    if file_type == "xlsx":
        if not content.startswith(b"PK\x03\x04"):
            raise ValidationAppError("File không phải Excel (.xlsx) hợp lệ.")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = archive.namelist()
                total = sum(info.file_size for info in archive.infolist())
        except zipfile.BadZipFile as exc:
            raise ValidationAppError("File Excel bị hỏng hoặc sai định dạng.") from exc
        if "xl/workbook.xml" not in names:
            raise ValidationAppError("File không phải Excel (.xlsx) hợp lệ.")
        if total > _MAX_UNZIPPED_BYTES:
            raise ValidationAppError("File Excel giải nén quá lớn, hệ thống không xử lý được.")
    elif file_type == "xls":
        if not content.startswith(_XLS_MAGIC):
            raise ValidationAppError("File không phải Excel (.xls) hợp lệ.")
    else:
        if content.startswith((b"PK\x03\x04", _XLS_MAGIC)):
            raise ValidationAppError("File có đuôi .csv nhưng thực chất là file Excel.")
        is_utf16 = content.startswith((b"\xff\xfe", b"\xfe\xff"))
        if not is_utf16 and b"\x00" in content[:8192]:
            raise ValidationAppError("File không phải văn bản CSV hợp lệ.")


def _build_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Từ bảng thô (không header) -> bảng có tiêu đề thật, bỏ dòng/cột trống hoàn toàn."""
    raw = raw.fillna("").astype(str)
    blank = raw.apply(lambda col: col.str.strip() == "")
    raw = raw[~blank.all(axis=1)].reset_index(drop=True)
    if raw.empty:
        raise ValidationAppError("File không có dữ liệu.")
    header_row = detect_header_row(raw)
    headers = [str(v).strip().lstrip("﻿") for v in raw.iloc[header_row]]
    data = raw.iloc[header_row + 1 :].reset_index(drop=True)

    # Bỏ cột thừa: không có tên và không có dữ liệu (thường do dấu phẩy thừa ở cuối dòng).
    keep = [i for i, h in enumerate(headers) if h or (data.iloc[:, i].str.strip() != "").any()]
    headers = [headers[i] for i in keep]
    data = data.iloc[:, keep].copy()

    seen: dict[str, int] = {}
    names: list[str] = []
    for position, header in enumerate(headers, start=1):
        base = header or f"cot_{position}"
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    data.columns = names
    if data.empty or not names:
        raise ValidationAppError("File không có dữ liệu (chỉ có dòng tiêu đề).")
    return data.reset_index(drop=True)


def _check_limits(frame: pd.DataFrame) -> None:
    if len(frame.columns) > settings.MAX_UPLOAD_COLUMNS:
        raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_COLUMNS} cột.")
    if len(frame) > settings.MAX_UPLOAD_ROWS:
        raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_ROWS:,} dòng.")


def read_csv_file(file_bytes: bytes, encoding: str, delimiter: str) -> pd.DataFrame:
    """Đọc file CSV thành DataFrame, mọi cột đọc dưới dạng str (dtype=str)."""
    try:
        text_sample = file_bytes[:_SAMPLE_BYTES].decode(encoding, errors="replace")
        width = 0
        for index, row in enumerate(csv.reader(io.StringIO(text_sample), delimiter=delimiter)):
            width = max(width, len(row))
            if index >= _SAMPLE_LINES:
                break
        if width == 0:
            raise ValidationAppError("File không có dữ liệu.")
        if width > settings.MAX_UPLOAD_COLUMNS:
            raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_COLUMNS} cột.")
        raw = pd.read_csv(
            io.BytesIO(file_bytes),
            header=None,
            names=range(width),
            dtype=str,
            keep_default_na=False,
            encoding=encoding,
            encoding_errors="replace",
            sep=delimiter,
            skip_blank_lines=True,
        )
    except ValidationAppError:
        raise
    except EmptyDataError as exc:
        raise ValidationAppError("File không có dữ liệu.") from exc
    except (ParserError, UnicodeError, csv.Error, ValueError) as exc:
        raise ValidationAppError(
            "Không đọc được file CSV: cấu trúc dòng/cột không nhất quán hoặc file bị hỏng."
        ) from exc
    if not encoding.lower().replace("_", "-").startswith(("utf-8", "utf8", "ascii")):
        # Các bảng mã cũ (cp1258...) giải mã ra chữ có dấu dạng tổ hợp: gom về dạng chuẩn NFC
        # để "Nguyễn" luôn là cùng một chuỗi, nếu không so sánh/loại trùng sẽ sai.
        raw = raw.apply(lambda col: col.map(lambda v: unicodedata.normalize("NFC", str(v))))
    frame = _build_frame(raw)
    _check_limits(frame)
    return frame


def _open_excel(file_bytes: bytes) -> pd.ExcelFile:
    engine = "xlrd" if file_bytes.startswith(_XLS_MAGIC) else "openpyxl"
    try:
        return pd.ExcelFile(io.BytesIO(file_bytes), engine=engine)
    except Exception as exc:  # noqa: BLE001 - thư viện đọc Excel ném nhiều loại lỗi khác nhau
        raise ValidationAppError("Không đọc được file Excel. File có thể bị hỏng.") from exc


def list_excel_sheets(file_bytes: bytes) -> list[str]:
    """Trả về danh sách tên sheet có trong file Excel."""
    return [str(name) for name in _open_excel(file_bytes).sheet_names]


def _tidy_excel_dates(frame: pd.DataFrame) -> pd.DataFrame:
    """Ô ngày của Excel đọc ra dạng 'YYYY-MM-DD 00:00:00': nếu cả cột chỉ có ngày thì cắt giờ."""
    for column in frame.columns:
        values = frame[column]
        filled = values[values.str.strip() != ""]
        if len(filled) and filled.map(lambda v: bool(_DATE_ONLY.match(v))).all():
            frame[column] = values.map(lambda v: v[:10] if _DATE_ONLY.match(v) else v)
    return frame


def read_excel_sheet(file_bytes: bytes, sheet_name: str) -> pd.DataFrame:
    """Đọc một sheet cụ thể của file Excel thành DataFrame, mọi cột đọc dưới dạng str."""
    workbook = _open_excel(file_bytes)
    if sheet_name not in [str(n) for n in workbook.sheet_names]:
        raise ValidationAppError("Sheet không tồn tại trong file.")
    try:
        raw = workbook.parse(sheet_name=sheet_name, header=None, dtype=str, keep_default_na=False)
    except Exception as exc:  # noqa: BLE001
        raise ValidationAppError("Không đọc được sheet này. File có thể bị hỏng.") from exc
    if raw.empty:
        raise ValidationAppError("Sheet này không có dữ liệu.")
    frame = _tidy_excel_dates(_build_frame(raw))
    _check_limits(frame)
    return frame


def read_dataset_file(
    file_bytes: bytes, filename: str, sheet_name: str | None = None
) -> ReadResult:
    """Điểm vào chung: nhận diện CSV hay Excel từ đuôi file và nội dung rồi đọc thành DataFrame."""
    file_type = file_type_from_name(filename)
    check_file_signature(file_type, file_bytes)
    if file_type == "csv":
        encoding = detect_encoding(file_bytes)
        text = file_bytes[:_SAMPLE_BYTES].decode(encoding, errors="replace")
        delimiter = detect_delimiter(text)
        return ReadResult(read_csv_file(file_bytes, encoding, delimiter), [], None, encoding)
    sheets = list_excel_sheets(file_bytes)
    if not sheets:
        raise ValidationAppError("File Excel không có sheet nào.")
    used = sheet_name if sheet_name is not None else sheets[0]
    return ReadResult(read_excel_sheet(file_bytes, used), sheets, used, None)
