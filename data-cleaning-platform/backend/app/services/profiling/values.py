"""Hàm dùng chung cho profiling và detector: nhận diện ô trống, email, SĐT, ngày, số.

Mọi hàm nhận GIÁ TRỊ CHUỖI (dữ liệu luôn đọc dtype=str). Các hàm đắt (phonenumbers, strptime) được
cache và chỉ gọi trên giá trị duy nhất của cột (xem `map_unique`) để cột 1 triệu dòng vẫn nhanh.
"""

import json
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import phonenumbers
from unidecode import unidecode

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

with open(DATA_DIR / "null_tokens.json", encoding="utf-8") as _file:
    NULL_TOKENS: frozenset[str] = frozenset(t.strip().lower() for t in json.load(_file)) | {""}

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
_PHONE_STRIP_RE = re.compile(r"[\s.\-()]")
_PHONE_LIKE_RE = re.compile(r"^(?:\+?84|0)\d{8,10}$")
_NUMBER_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_BOOLEAN_WORDS = frozenset({"true", "false", "yes", "no", "có", "không", "đúng", "sai"})

# (nhãn hiển thị, regex nhận diện hình dạng, các định dạng strptime thử theo thứ tự)
_DATE_PATTERNS: list[tuple[str, re.Pattern[str], list[tuple[str, str]]]] = [
    ("yyyy-MM-dd", re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"), [("yyyy-MM-dd", "%Y-%m-%d")]),
    ("yyyy/MM/dd", re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"), [("yyyy/MM/dd", "%Y/%m/%d")]),
    (
        "dd/MM/yyyy",
        re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
        [("dd/MM/yyyy", "%d/%m/%Y"), ("MM/dd/yyyy", "%m/%d/%Y")],
    ),
    ("dd-MM-yyyy", re.compile(r"^\d{1,2}-\d{1,2}-\d{4}$"), [("dd-MM-yyyy", "%d-%m-%Y")]),
    ("dd.MM.yyyy", re.compile(r"^\d{1,2}\.\d{1,2}\.\d{4}$"), [("dd.MM.yyyy", "%d.%m.%Y")]),
    (
        "yyyy-MM-dd HH:mm:ss",
        re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?$"),
        [("yyyy-MM-dd HH:mm:ss", "%Y-%m-%d %H:%M:%S"), ("yyyy-MM-dd HH:mm:ss", "%Y-%m-%d %H:%M")],
    ),
]


# ---------------------------------------------------------------- ô trống


def is_null(value: Any) -> bool:
    """Ô trống: None/NaN, chuỗi rỗng/khoảng trắng hoặc một token coi như null (N/A, -, null...)."""
    if value is None or (isinstance(value, float) and value != value):
        return True
    return str(value).strip().lower() in NULL_TOKENS


def null_mask(series: pd.Series) -> pd.Series:
    """Mặt nạ boolean: True ở ô trống (gồm cả null-token)."""
    return series.fillna("").astype(str).str.strip().str.lower().isin(NULL_TOKENS)


def non_null_values(series: pd.Series) -> pd.Series:
    """Các giá trị không trống của cột, đã cắt khoảng trắng hai đầu (giữ nguyên nhãn dòng)."""
    return series[~null_mask(series)].astype(str).str.strip()


def map_unique(series: pd.Series, func: Callable[[str], Any]) -> pd.Series:
    """Áp `func` lên từng giá trị DUY NHẤT rồi phân phối lại về cả cột (nhanh cho cột lặp nhiều)."""
    mapping = {value: func(value) for value in series.unique()}
    return series.map(mapping)


# ---------------------------------------------------------------- email


def is_email(value: str) -> bool:
    """Email đúng cú pháp cơ bản (đã cắt khoảng trắng)."""
    return bool(_EMAIL_RE.match(value.strip()))


# ---------------------------------------------------------------- điện thoại


def looks_like_phone(value: str) -> bool:
    """Trông giống số điện thoại VN (0xxxxxxxxx hoặc +84xxxxxxxxx, cho phép khoảng trắng/dấu)."""
    return bool(_PHONE_LIKE_RE.match(_PHONE_STRIP_RE.sub("", value.strip())))


@lru_cache(maxsize=100_000)
def is_valid_phone(value: str) -> bool:
    """Số điện thoại VN hợp lệ theo thư viện phonenumbers."""
    cleaned = _PHONE_STRIP_RE.sub("", value.strip())
    try:
        return phonenumbers.is_valid_number(phonenumbers.parse(cleaned, "VN"))
    except phonenumbers.NumberParseException:
        return False


def phone_shape(value: str) -> str:
    """Kiểu trình bày của số điện thoại, để phát hiện cột viết lẫn nhiều kiểu."""
    text = value.strip()
    if text.startswith("+"):
        return "quốc tế (+84)"
    if re.search(r"\s", text):
        return "có khoảng trắng"
    if re.search(r"[.\-()]", text):
        return "có dấu phân cách"
    return "chỉ gồm chữ số"


# ---------------------------------------------------------------- ngày


@lru_cache(maxsize=100_000)
def parse_date(value: str) -> tuple[str, datetime] | None:
    """(nhãn định dạng, thời điểm) nếu là ngày hợp lệ; ngày không có thật (31/02) -> None."""
    text = value.strip()
    for _label, pattern, formats in _DATE_PATTERNS:
        if not pattern.match(text):
            continue
        candidate = text.replace("T", " ") if "T" in text else text
        for name, fmt in formats:
            try:
                return name, datetime.strptime(candidate, fmt)
            except ValueError:
                continue
        return None
    return None


def date_format_of(value: str) -> str | None:
    """Nhãn định dạng ngày (vd. 'dd/MM/yyyy') hoặc None nếu không phải ngày hợp lệ."""
    parsed = parse_date(value)
    return parsed[0] if parsed else None


# ---------------------------------------------------------------- số, boolean


def is_integer(value: str) -> bool:
    return bool(_INT_RE.match(value.strip()))


def is_number(value: str) -> bool:
    return bool(_NUMBER_RE.match(value.strip()))


def to_number(value: str) -> float | None:
    """Chuỗi số (cho phép dấu phẩy thập phân) -> float; không phải số -> None."""
    text = value.strip()
    if not _NUMBER_RE.match(text):
        return None
    return float(text.replace(",", "."))


def is_boolean(value: str) -> bool:
    return value.strip().lower() in _BOOLEAN_WORDS


def format_number(value: float) -> str:
    """Số gọn: 29.0 -> '29', 3.5 -> '3.5'."""
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


# ---------------------------------------------------------------- văn bản


def normalize_key(value: str) -> str:
    """Khóa so sánh: bỏ dấu, hạ chữ thường, chỉ giữ chữ-số ('TP. Hồ Chí Minh' -> 'tphochiminh')."""
    text = unidecode(unicodedata.normalize("NFC", value)).lower()
    return re.sub(r"[^a-z0-9]", "", text)


def percent(part: int, total: int) -> str:
    """'12,5%' (dấu phẩy thập phân kiểu Việt Nam)."""
    return f"{(part / total * 100 if total else 0):.1f}%".replace(".", ",")
