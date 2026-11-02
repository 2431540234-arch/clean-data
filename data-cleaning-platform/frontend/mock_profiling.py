"""Profiling và điểm chất lượng cho mock_api (xấp xỉ đơn giản của backend, đủ để demo).

Chỉ mô phỏng định dạng dữ liệu trả về (SchemaProfileOut, QualityReportOut); thuật toán thật nằm ở
backend/app/services/profiling và quality.py. Công thức điểm theo docs/quality_score.md.
"""

import re
import unicodedata
from collections import Counter
from datetime import datetime

import pandas as pd

from mock_data import is_null

_MATCH_THRESHOLD = 0.8  # tỉ lệ giá trị khớp tối thiểu để kết luận kiểu của cột
_SAMPLE_SIZE = 5
_OUTLIER_IQR_FACTOR = 3.0
_MIN_VALUES_FOR_OUTLIERS = 8

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^(\+?84|0)\d{8,10}$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?\d+[.,]\d+$")
_BOOLEAN_WORDS = frozenset({"true", "false", "yes", "no", "có", "không", "đúng", "sai"})
_DATE_FORMATS = {
    "dd/MM/yyyy": "%d/%m/%Y",
    "yyyy-MM-dd": "%Y-%m-%d",
    "dd-MM-yyyy": "%d-%m-%Y",
    "dd.MM.yyyy": "%d.%m.%Y",
}

WEIGHTS = {"completeness": 0.3, "uniqueness": 0.2, "validity": 0.3, "consistency": 0.2}


def _is_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value))


def _is_phone(value: str) -> bool:
    return bool(_PHONE_RE.match(re.sub(r"[\s.\-()]", "", value)))


def _date_format(value: str) -> str | None:
    for label, fmt in _DATE_FORMATS.items():
        try:
            datetime.strptime(value, fmt)
        except ValueError:
            continue
        return label
    return None


def _as_float(value: str) -> float | None:
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def _non_null(series: pd.Series) -> list[str]:
    return [str(v).strip() for v in series if not is_null(v)]


def infer_type(values: list[str]) -> str:
    """Kiểu của cột theo thứ tự email, phone, date, integer, float, boolean, text."""
    if not values:
        return "text"

    def share(predicate) -> float:
        return sum(1 for v in values if predicate(v)) / len(values)

    checks = (
        ("email", _is_email),
        ("phone", _is_phone),
        ("date", lambda v: _date_format(v) is not None),
        ("integer", lambda v: bool(_INT_RE.match(v))),
        ("float", lambda v: bool(_INT_RE.match(v) or _FLOAT_RE.match(v))),
        ("boolean", lambda v: v.lower() in _BOOLEAN_WORDS),
    )
    for name, predicate in checks:
        if share(predicate) >= _MATCH_THRESHOLD:
            return name
    return "text"


def _detected_format(values: list[str]) -> str | None:
    counts = Counter(f for f in (_date_format(v) for v in values) if f)
    if not counts:
        return None
    if len(counts) == 1:
        return next(iter(counts))
    return "Nhiều định dạng: " + ", ".join(label for label, _ in counts.most_common())


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def profile_frame(frame: pd.DataFrame, version_id: int, first_id: int, now: str) -> list[dict]:
    """Danh sách SchemaProfileOut của mọi cột trong frame."""
    total = len(frame)
    profiles = []
    for index, name in enumerate(frame.columns):
        values = _non_null(frame[name])
        inferred = infer_type(values)
        numbers = [n for n in (_as_float(v) for v in values) if n is not None]
        numeric = inferred in {"integer", "float"} and numbers
        distinct = list(dict.fromkeys(values))
        profiles.append(
            {
                "id": first_id + index,
                "version_id": version_id,
                "column_name": str(name),
                "column_index": index,
                "inferred_type": inferred,
                "null_count": total - len(values),
                "unique_count": len(distinct),
                "null_ratio": (total - len(values)) / total if total else 0.0,
                "unique_ratio": len(distinct) / total if total else 0.0,
                "min_value": _format_number(min(numbers)) if numeric else None,
                "max_value": _format_number(max(numbers)) if numeric else None,
                "mean_value": round(sum(numbers) / len(numbers), 2) if numeric else None,
                "sample_values": distinct[:_SAMPLE_SIZE],
                "detected_format": _detected_format(values) if inferred == "date" else None,
                "created_at": now,
            }
        )
    return profiles


def _normalize(value: str) -> str:
    """Bỏ dấu, hạ chữ thường, chỉ giữ chữ-số: dùng để gom các biến thể của cùng một giá trị."""
    text = unicodedata.normalize("NFD", value.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _outlier_count(numbers: list[float]) -> int:
    if len(numbers) < _MIN_VALUES_FOR_OUTLIERS:
        return 0
    ordered = sorted(numbers)
    q1, q3 = ordered[len(ordered) // 4], ordered[(3 * len(ordered)) // 4]
    spread = _OUTLIER_IQR_FACTOR * (q3 - q1)
    return sum(1 for n in numbers if n < q1 - spread or n > q3 + spread)


def quality_report(frame: pd.DataFrame, version_id: int, report_id: int, now: str) -> dict:
    """QualityReportOut tính từ frame (overall_score trên thang 0..100, thành phần 0..1)."""
    rows, cols = len(frame), len(frame.columns)
    cells = rows * cols or 1

    missing_cells = sum(1 for col in frame.columns for v in frame[col] if is_null(v))
    duplicate_rows = int(frame.duplicated().sum()) if rows else 0

    valid_checked = invalid = 0
    text_cells = inconsistent = 0
    for col in frame.columns:
        values = _non_null(frame[col])
        kind = infer_type(values)
        if kind in {"email", "phone", "date", "integer", "float"}:
            check = {
                "email": _is_email,
                "phone": _is_phone,
                "date": lambda v: _date_format(v) is not None,
                "integer": lambda v: bool(_INT_RE.match(v)),
                "float": lambda v: bool(_INT_RE.match(v) or _FLOAT_RE.match(v)),
            }[kind]
            valid_checked += len(values)
            invalid += sum(1 for v in values if not check(v))
            if kind in {"integer", "float"}:
                numbers = [n for n in (_as_float(v) for v in values) if n is not None]
                invalid += _outlier_count(numbers)
        elif kind == "text":
            groups: dict[str, set[str]] = {}
            for v in values:
                groups.setdefault(_normalize(v), set()).add(v)
            text_cells += len(values)
            counts = Counter(values)
            inconsistent += sum(
                counts[v] for variants in groups.values() if len(variants) > 1 for v in variants
            )

    components = {
        "completeness": 1 - missing_cells / cells,
        "uniqueness": 1 - duplicate_rows / rows if rows else 1.0,
        "validity": 1 - min(invalid, valid_checked) / valid_checked if valid_checked else 1.0,
        "consistency": 1 - inconsistent / text_cells if text_cells else 1.0,
    }
    score = 100 * sum(WEIGHTS[name] * value for name, value in components.items())
    return {
        "id": report_id,
        "version_id": version_id,
        "overall_score": round(score, 1),
        **{name: round(value, 4) for name, value in components.items()},
        "issue_summary": {
            "missing_cells": missing_cells,
            "duplicate_rows": duplicate_rows,
            "invalid_values": min(invalid, valid_checked),
            "inconsistent_values": inconsistent,
        },
        "created_at": now,
    }
