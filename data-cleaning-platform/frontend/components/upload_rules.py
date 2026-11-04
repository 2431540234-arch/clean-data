"""Giới hạn dung lượng file tải lên và cách tải (một lần hay tự tách thành các phần).

Hàm thuần, không gọi Streamlit. Các hằng số khớp backend: MAX_CHUNKED_UPLOAD_MB (CSV),
MAX_UPLOAD_MB (Excel, tải một lần) và server.maxUploadSize trong .streamlit/config.toml.
"""

MAX_CSV_MB = 200  # CSV: tới mức này, file lớn được tự tách thành các phần khi gửi
MAX_EXCEL_MB = 50  # Excel luôn phải đọc cả file vào bộ nhớ nên giữ trần thấp hơn
CHUNK_THRESHOLD_MB = 20  # CSV lớn hơn mức này thì tải theo từng phần

_MB = 1024 * 1024


def is_csv(name: str) -> bool:
    return name.lower().endswith(".csv")


def size_problem(name: str, size: int) -> str | None:
    """Thông báo lỗi nếu file vượt trần của loại file (CSV 200 MB, Excel 50 MB), ngược lại None."""
    limit = MAX_CSV_MB if is_csv(name) else MAX_EXCEL_MB
    if size <= limit * _MB:
        return None
    if is_csv(name):
        return f"File vượt quá {MAX_CSV_MB} MB."
    return (
        f"File Excel vượt quá {MAX_EXCEL_MB} MB. Hãy lưu thành CSV (hỗ trợ tới {MAX_CSV_MB} MB, "
        "tự tách thành nhiều phần khi tải lên) rồi thử lại."
    )


def use_parts(name: str, size: int) -> bool:
    """CSV lớn hơn ngưỡng thì tải theo từng phần; Excel và file nhỏ tải một lần."""
    return is_csv(name) and size > CHUNK_THRESHOLD_MB * _MB


# Một sheet Excel có 1.048.576 dòng, trừ 1 dòng tiêu đề (khớp backend services/export.py).
EXCEL_MAX_DATA_ROWS = 1_048_575


def excel_row_problem(rows: int) -> str | None:
    """Thông báo nếu `rows` dòng dữ liệu không vừa một sheet Excel (gợi ý CSV), ngược lại None."""
    if rows <= EXCEL_MAX_DATA_ROWS:
        return None
    shown = f"{rows:,}".replace(",", ".")
    limit = f"{EXCEL_MAX_DATA_ROWS:,}".replace(",", ".")
    return (
        f"Phiên bản này có {shown} dòng, vượt giới hạn {limit} dòng dữ liệu của một sheet Excel. "
        "Hãy xuất CSV để lấy đủ dữ liệu (CSV không giới hạn số dòng); "
        "hệ thống không tự cắt dữ liệu."
    )
