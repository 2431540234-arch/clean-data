"""Dò encoding của file văn bản (utf-8, cp1258, ...) bằng charset-normalizer."""


def detect_encoding(file_bytes: bytes) -> str:
    """Trả về tên encoding khả năng cao nhất của nội dung file.

    Gợi ý cách làm: dùng charset_normalizer.from_bytes(file_bytes).best() rồi lấy
    thuộc tính .encoding; nếu không xác định được, fallback về "utf-8".
    """
    raise NotImplementedError(
        "TODO: dùng charset_normalizer để dò encoding, fallback 'utf-8' nếu không chắc."
    )
