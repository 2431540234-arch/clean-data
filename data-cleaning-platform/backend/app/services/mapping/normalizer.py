"""Chuẩn hóa tên cột: bỏ dấu tiếng Việt, lowercase, bỏ ký tự đặc biệt."""


def normalize_column_name(raw_name: str) -> str:
    """Chuẩn hóa tên cột về dạng không dấu, lowercase, dùng underscore.

    Gợi ý cách làm: dùng Unidecode(raw_name) để bỏ dấu, .lower(), rồi regex thay
    khoảng trắng/ký tự đặc biệt bằng "_".
    """
    raise NotImplementedError("TODO: dùng Unidecode + lowercase + regex để chuẩn hóa tên cột.")
