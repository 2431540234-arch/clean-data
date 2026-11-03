"""Chuẩn hóa tên cột: bỏ dấu tiếng Việt, lowercase, bỏ ký tự đặc biệt."""

import re
import unicodedata

from unidecode import unidecode

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_column_name(raw_name: str) -> str:
    """Chuẩn hóa tên cột về dạng không dấu, lowercase, nối bằng dấu gạch dưới.

    Ví dụ: "Tỉnh/Thành phố" -> "tinh_thanh_pho", "Số ĐT" -> "so_dt", " E-mail " -> "e_mail".
    """
    text = unidecode(unicodedata.normalize("NFC", str(raw_name))).lower()
    return _NON_ALNUM_RE.sub("_", text).strip("_")
