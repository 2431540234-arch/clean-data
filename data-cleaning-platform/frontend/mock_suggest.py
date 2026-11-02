"""Bộ sinh gợi ý làm sạch cho mock_api: phát hiện vấn đề từ dữ liệu rồi đề xuất rule JSON.

Mô phỏng backend/app/services/detectors + ai/suggester. Gợi ý nguồn "rule_engine" đến từ phát hiện
tất định; nguồn "ai" mô phỏng đề xuất cần phán đoán (chuẩn hóa tên tỉnh, điền giá trị thiếu).
Chạy lại trên dữ liệu đã sạch thì không còn gợi ý nào.
"""

import re
import statistics
from collections import Counter, defaultdict
from typing import Any

import pandas as pd

from mock_data import is_null
from mock_profiling import _date_format, _is_email, _is_phone, _non_null, infer_type
from mock_rules import _number

_MIN_NUMERIC_FOR_OUTLIERS = 8
_MIN_MISSING_RATIO_TO_FILL = 0.05
_E164_RE = re.compile(r"^\+84\d{9,10}$")
_CANONICAL_DATE = "yyyy-MM-dd"

# Rút gọn từ backend/app/data/provinces_vn.json.
PROVINCES = {
    "TP. Hồ Chí Minh": [
        "HCM", "TP.HCM", "TPHCM", "TP HCM", "Ho Chi Minh", "Hồ Chí Minh", "Sài Gòn", "Saigon",
    ],
    "Hà Nội": ["HN", "Ha Noi", "TP. Hà Nội", "TP Ha Noi"],
    "Đà Nẵng": ["DN", "Da Nang", "TP. Đà Nẵng"],
    "Cần Thơ": ["Can Tho", "TP. Cần Thơ"],
    "Hải Phòng": ["HP", "Hai Phong", "TP. Hải Phòng"],
}  # fmt: skip
_CANONICAL_BY_ALIAS = {
    alias.lower(): canonical for canonical, aliases in PROVINCES.items() for alias in aliases
}


def _suggestion(
    kind: str,
    source: str,
    column: str | None,
    step: dict[str, Any],
    explanation: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "issue_id": None,
        "suggestion_type": kind,
        "source": source,
        "target_column": column,
        "proposed_rule": {"steps": [step]},
        "explanation": explanation,
        "confidence": confidence,
    }


def _step(op: str, column: str | None, **params: Any) -> dict[str, Any]:
    return {"op": op, "column": column, "params": params}


def _outlier_count(numbers: list[float]) -> int:
    ordered = sorted(numbers)
    q1, q3 = ordered[len(ordered) // 4], ordered[(3 * len(ordered)) // 4]
    spread = 1.5 * (q3 - q1)
    return sum(1 for n in numbers if n < q1 - spread or n > q3 + spread)


def _province_mapping(values: list[str]) -> dict[str, str]:
    """Từ khóa biến thể -> tên chuẩn, chỉ khi cột có ít nhất 2 cách viết cùng một tỉnh."""
    spellings: dict[str, set[str]] = defaultdict(set)
    for value in set(values):
        canonical = _CANONICAL_BY_ALIAS.get(value.strip().lower())
        if canonical is None and value in PROVINCES:
            canonical = value
        if canonical:
            spellings[canonical].add(value)
    mapping: dict[str, str] = {}
    for canonical, variants in spellings.items():
        if len(variants) > 1 or (variants and canonical not in variants):
            mapping.update({v: canonical for v in variants if v != canonical})
    return mapping


def generate(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Danh sách gợi ý (chưa có id/version/status) cho một DataFrame."""
    found: list[dict[str, Any]] = []

    duplicates = int(frame.duplicated().sum()) if len(frame) else 0
    if duplicates:
        found.append(
            _suggestion(
                "fix",
                "rule_engine",
                None,
                _step("drop_duplicates", None, keep="first"),
                f"Phát hiện {duplicates} dòng trùng lặp hoàn toàn với dòng khác. "
                "Giữ dòng đầu tiên và xóa các dòng còn lại.",
                0.99,
            )
        )

    for column in map(str, frame.columns):
        if column.endswith("_is_outlier"):
            continue  # cột cờ do chính rule flag_outliers sinh ra
        values = _non_null(frame[column])
        raw = [str(v) for v in frame[column] if not is_null(v)]
        kind = infer_type(values)

        padded = sum(1 for r in raw if r != r.strip())
        if padded:
            found.append(
                _suggestion(
                    "fix",
                    "rule_engine",
                    column,
                    _step("trim_whitespace", column),
                    f"Cột “{column}” có {padded} giá trị thừa khoảng trắng ở đầu hoặc cuối. "
                    "Cắt khoảng trắng để các giá trị giống nhau được nhận ra là một.",
                    0.99,
                )
            )

        if kind == "email":
            messy = sum(1 for v in values if v != v.lower())
            invalid = sum(1 for v in values if not _is_email(v))
            if messy:
                note = (
                    f" Có {invalid} email sai cú pháp được giữ nguyên để bạn kiểm tra."
                    if invalid
                    else ""
                )
                found.append(
                    _suggestion(
                        "fix",
                        "rule_engine",
                        column,
                        _step("standardize_email", column, drop_invalid=False),
                        f"Cột “{column}” có {messy} email viết hoa lẫn chữ thường. "
                        f"Chuyển về chữ thường.{note}",
                        0.95,
                    )
                )
            elif invalid:
                found.append(
                    _suggestion(
                        "fix",
                        "ai",
                        column,
                        _step("standardize_email", column, drop_invalid=True),
                        f"Cột “{column}” còn {invalid} email sai cú pháp. Đặt các ô này về trống "
                        "để không lẫn vào dữ liệu hợp lệ. Giá trị gốc sẽ mất, hãy cân nhắc.",
                        0.6,
                    )
                )
        elif kind == "phone":
            irregular = sum(1 for v in values if _is_phone(v) and not _E164_RE.match(v))
            if irregular:
                found.append(
                    _suggestion(
                        "fix",
                        "rule_engine",
                        column,
                        _step("standardize_phone", column, region="VN", output_format="E164"),
                        f"Cột “{column}” có {irregular} số điện thoại viết theo nhiều kiểu "
                        "(có khoảng trắng, gạch nối, +84). Chuẩn hóa về dạng +84xxxxxxxxx.",
                        0.95,
                    )
                )
        elif kind == "date":
            formats = Counter(f for f in (_date_format(v) for v in values) if f)
            if len(formats) > 1 or (formats and _CANONICAL_DATE not in formats):
                listed = ", ".join(f"{name} ({count})" for name, count in formats.most_common())
                found.append(
                    _suggestion(
                        "fix",
                        "rule_engine",
                        column,
                        _step("standardize_date", column, output_format="%Y-%m-%d", dayfirst=True),
                        f"Cột “{column}” lẫn nhiều định dạng ngày: {listed}. "
                        "Chuẩn hóa về yyyy-mm-dd (ưu tiên ngày trước tháng).",
                        0.9,
                    )
                )
        elif kind in {"integer", "float"}:
            already_flagged = f"{column}_is_outlier" in frame.columns
            numbers = [n for n in (_number(v) for v in values) if n is not None]
            if len(numbers) >= _MIN_NUMERIC_FOR_OUTLIERS and not already_flagged:
                outliers = _outlier_count(numbers)
                if outliers:
                    found.append(
                        _suggestion(
                            "rule",
                            "rule_engine",
                            column,
                            _step("flag_outliers", column, method="iqr", threshold=1.5),
                            f"Cột “{column}” có {outliers} giá trị bất thường so với phần còn lại "
                            "(ví dụ âm hoặc quá lớn). Chỉ đánh dấu bằng cột cờ, không xóa dữ liệu.",
                            0.88,
                        )
                    )
            missing = len(frame) - len(values)
            if numbers and len(frame) and missing / len(frame) >= _MIN_MISSING_RATIO_TO_FILL:
                median = statistics.median(numbers)
                found.append(
                    _suggestion(
                        "fix",
                        "ai",
                        column,
                        _step("fill_missing", column, strategy="median"),
                        f"Cột “{column}” thiếu {missing} giá trị. Điền bằng trung vị ({median:g}) "
                        "ít bị ảnh hưởng bởi giá trị bất thường. Hãy cân nhắc trước khi chấp nhận.",
                        0.62,
                    )
                )
        elif kind == "text":
            mapping = _province_mapping(values)
            if mapping:
                found.append(
                    _suggestion(
                        "fix",
                        "ai",
                        column,
                        _step("replace_values", column, mapping=mapping),
                        f"Cột “{column}” viết cùng một tỉnh/thành theo nhiều cách "
                        f"({', '.join(sorted(mapping))}…). Thống nhất về tên chuẩn.",
                        0.82,
                    )
                )
    return found
