"""Dò encoding của file văn bản (utf-8, cp1258, ...) bằng charset-normalizer."""

import codecs

from charset_normalizer import from_bytes

# Chỉ xét phần đầu file: đủ để đoán encoding mà không tốn thời gian với file lớn.
_SAMPLE_BYTES = 200_000


def detect_encoding(file_bytes: bytes) -> str:
    """Trả về tên encoding khả năng cao nhất của nội dung file (fallback 'utf-8').

    Thứ tự: BOM -> UTF-8 hợp lệ (phổ biến nhất, không cần đoán) -> charset-normalizer.
    """
    if file_bytes.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if file_bytes.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    sample = file_bytes[:_SAMPLE_BYTES]
    try:
        sample.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError as exc:
        # Mẫu có thể bị cắt giữa một ký tự nhiều byte: nếu lỗi nằm ở đuôi mẫu thì vẫn là UTF-8.
        if exc.start >= len(sample) - 3 and len(file_bytes) > len(sample):
            return "utf-8"
    best = from_bytes(sample).best()
    if best is None or not best.encoding:
        return "utf-8"
    return best.encoding
