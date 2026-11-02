"""Rule Engine giả cho mock_api: thực thi RuleSet (DSL trong docs/rule_dsl.md) bằng pandas.

Mô phỏng hành vi của backend/app/services/rules để mock có trạng thái thật (áp dụng rule tạo version
mới, xem trước có diff từng ô). Dữ liệu là DataFrame toàn chuỗi; ô thiếu có thể là "" hoặc
null-token. Mỗi op trả (DataFrame mới, tập nhãn dòng bị ảnh hưởng); nhãn dòng là index gốc của df.
"""

import re
import statistics
from collections.abc import Callable
from datetime import datetime
from typing import Any

import pandas as pd

from mock_data import is_null

ALLOWED_OPS = (
    "trim_whitespace",
    "change_case",
    "replace_values",
    "standardize_date",
    "standardize_phone",
    "standardize_email",
    "cast_type",
    "fill_missing",
    "drop_duplicates",
    "drop_rows_where",
    "flag_outliers",
    "rename_column",
    "drop_column",
)
OPS_WITHOUT_REQUIRED_COLUMN = ("drop_duplicates",)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")
_MIN_VALUES_FOR_OUTLIERS = 4


class RuleError(Exception):
    """Rule không thực thi được; message là thông báo tiếng Việt cho người dùng."""


Result = tuple[pd.DataFrame, set[Any]]


def _number(value: str) -> float | None:
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def _map_column(df: pd.DataFrame, column: str, func: Callable[[str], str]) -> Result:
    """Áp func lên các ô không thiếu của một cột; trả df mới và các dòng có giá trị đổi."""
    old = df[column]
    new = old.map(lambda v: v if is_null(v) else func(str(v)))
    changed = old.index[(old != new).to_numpy()]
    result = df.copy()
    result[column] = new
    return result, set(changed)


# ---------------------------------------------------------------- các op


def _trim(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    return _map_column(df, str(column), lambda s: s.strip())


def _change_case(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    modes = {
        "upper": str.upper,
        "lower": str.lower,
        "title": str.title,
        "capitalize": str.capitalize,
    }
    mode = params.get("mode")
    if mode not in modes:
        raise RuleError("Tham số mode phải là upper, lower, title hoặc capitalize.")
    return _map_column(df, str(column), modes[mode])


def _replace_values(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    mapping = params.get("mapping")
    if not isinstance(mapping, dict):
        raise RuleError("Tham số mapping phải là một từ điển giá trị cũ -> giá trị mới.")
    return _map_column(df, str(column), lambda s: str(mapping.get(s, s)))


def _parse_date(text: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _standardize_date(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    output = params.get("output_format", "%Y-%m-%d")

    def convert(text: str) -> str:
        parsed = _parse_date(text)
        return parsed.strftime(output) if parsed else text  # không parse được thì giữ nguyên

    return _map_column(df, str(column), convert)


def _standardize_phone(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    fmt = params.get("output_format", "E164")
    if fmt not in {"E164", "NATIONAL", "INTERNATIONAL"}:
        raise RuleError("output_format phải là E164, NATIONAL hoặc INTERNATIONAL.")

    def convert(text: str) -> str:
        digits = re.sub(r"[\s.\-()]", "", text)
        match = re.fullmatch(r"(?:\+?84|0)(\d{9,10})", digits)
        if not match:
            return text  # số không parse được thì giữ nguyên
        subscriber = match.group(1)
        if fmt == "E164":
            return f"+84{subscriber}"
        if fmt == "NATIONAL":
            return f"0{subscriber}"
        return f"+84 {subscriber[:2]} {subscriber[2:5]} {subscriber[5:]}"

    return _map_column(df, str(column), convert)


def _standardize_email(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    drop_invalid = bool(params.get("drop_invalid", False))

    def convert(text: str) -> str:
        cleaned = text.strip().lower()
        if _EMAIL_RE.match(cleaned):
            return cleaned
        return "" if drop_invalid else text

    return _map_column(df, str(column), convert)


def _cast_type(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    target = params.get("target_type")
    if target not in {"int", "float", "str"}:
        raise RuleError("Mock chỉ hỗ trợ ép kiểu int, float hoặc str.")
    on_error = params.get("on_error", "coerce")

    def convert(text: str) -> str:
        number = _number(text)
        if target == "str":
            return text.strip()
        if number is None:
            if on_error == "raise":
                raise RuleError(f"Giá trị “{text}” không ép được sang {target}.")
            return ""
        return str(int(number)) if target == "int" else f"{number:g}"

    return _map_column(df, str(column), convert)


def _fill_missing(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    strategy = params.get("strategy", "constant")
    values = list(df[str(column)])
    present = [str(v).strip() for v in values if not is_null(v)]
    numbers = [n for n in (_number(v) for v in present) if n is not None]
    if strategy == "constant":
        fills: list[str | None] = [str(params.get("value", ""))] * len(values)
    elif strategy in {"mean", "median"}:
        if not numbers:
            raise RuleError("Cột không có giá trị số để tính trung bình/trung vị.")
        value = statistics.fmean(numbers) if strategy == "mean" else statistics.median(numbers)
        fills = [f"{value:g}"] * len(values)
    elif strategy == "mode":
        if not present:
            raise RuleError("Cột không có giá trị nào để lấy giá trị phổ biến.")
        fills = [max(set(present), key=present.count)] * len(values)
    elif strategy in {"ffill", "bfill"}:
        order = range(len(values)) if strategy == "ffill" else range(len(values) - 1, -1, -1)
        fills, last = [None] * len(values), None
        for i in order:
            if is_null(values[i]):
                fills[i] = last
            else:
                last = str(values[i])
    else:
        raise RuleError("strategy phải là constant, mean, median, mode, ffill hoặc bfill.")

    result = df.copy()
    changed = set()
    new_values = []
    for label, current, fill in zip(df.index, values, fills, strict=True):
        if is_null(current) and fill is not None and fill != "":
            new_values.append(fill)
            changed.add(label)
        else:
            new_values.append(current)
    result[str(column)] = new_values
    return result, changed


def _drop_duplicates(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    subset = params.get("subset")
    if subset is not None:
        missing = [c for c in subset if c not in df.columns]
        if missing:
            raise RuleError(f"Cột “{missing[0]}” không tồn tại trong dữ liệu.")
    mask = df.duplicated(subset=subset, keep=params.get("keep", "first"))
    return df[~mask], set(df.index[mask.to_numpy()])


def _drop_rows_where(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    operator, target = params.get("operator"), params.get("value")
    series = df[str(column)]

    def compare(value: Any) -> bool:
        if operator == "is_null":
            return is_null(value)
        if operator == "is_not_null":
            return not is_null(value)
        if is_null(value):
            return False
        left, right = _number(value), _number(target) if target is not None else None
        if operator in {"gt", "lt", "gte", "lte"}:
            if left is None or right is None:
                return False
            return {
                "gt": left > right,
                "lt": left < right,
                "gte": left >= right,
                "lte": left <= right,
            }[operator]
        if operator in {"eq", "neq"}:
            equal = (
                left == right
                if left is not None and right is not None
                else str(value) == str(target)
            )
            return equal if operator == "eq" else not equal
        raise RuleError("operator không hợp lệ.")

    mask = series.map(compare)
    return df[~mask], set(df.index[mask.to_numpy()])


def _flag_outliers(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    method = params.get("method", "iqr")
    if method not in {"iqr", "zscore"}:
        raise RuleError("method phải là iqr hoặc zscore.")
    series = df[str(column)]
    numeric = pd.to_numeric(
        series.map(lambda v: None if is_null(v) else _number(v)), errors="coerce"
    )
    valid = numeric.dropna()
    flagged = pd.Series(False, index=df.index)
    if len(valid) >= _MIN_VALUES_FOR_OUTLIERS:
        if method == "iqr":
            threshold = float(params.get("threshold", 1.5))
            q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
            low, high = q1 - threshold * (q3 - q1), q3 + threshold * (q3 - q1)
            flagged = (numeric < low) | (numeric > high)
        else:
            threshold = float(params.get("threshold", 3))
            std = valid.std()
            flagged = ((numeric - valid.mean()).abs() / std > threshold) if std else flagged
    result = df.copy()
    result[f"{column}_is_outlier"] = flagged.map({True: "True", False: "False"})
    return result, set(df.index[flagged.fillna(False).to_numpy()])


def _rename_column(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    new_name = str(params.get("new_name", "")).strip()
    if not new_name:
        raise RuleError("Thiếu tên cột mới (new_name).")
    if new_name != column and new_name in df.columns:
        raise RuleError(f"Cột “{new_name}” đã tồn tại, không thể đổi tên trùng.")
    return df.rename(columns={column: new_name}), set()


def _drop_column(df: pd.DataFrame, column: str | None, params: dict[str, Any]) -> Result:
    return df.drop(columns=[str(column)]), set()


_OPS: dict[str, Callable[[pd.DataFrame, str | None, dict[str, Any]], Result]] = {
    "trim_whitespace": _trim,
    "change_case": _change_case,
    "replace_values": _replace_values,
    "standardize_date": _standardize_date,
    "standardize_phone": _standardize_phone,
    "standardize_email": _standardize_email,
    "cast_type": _cast_type,
    "fill_missing": _fill_missing,
    "drop_duplicates": _drop_duplicates,
    "drop_rows_where": _drop_rows_where,
    "flag_outliers": _flag_outliers,
    "rename_column": _rename_column,
    "drop_column": _drop_column,
}


# ---------------------------------------------------------------- RuleSet


def validate_steps(steps: Any) -> list[dict[str, Any]]:
    """Kiểm tra cấu trúc RuleSet.steps giống RuleStep của backend; trả danh sách bước."""
    if not isinstance(steps, list):
        raise RuleError("steps phải là một danh sách.")
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or step.get("op") not in ALLOWED_OPS:
            raise RuleError(f"Bước {index + 1}: op không được hỗ trợ bởi Rule Engine.")
        if step["op"] not in OPS_WITHOUT_REQUIRED_COLUMN and not step.get("column"):
            raise RuleError(f"Bước {index + 1}: op “{step['op']}” yêu cầu phải chỉ định column.")
    return steps


def apply_steps(
    df: pd.DataFrame, steps: list[dict[str, Any]]
) -> tuple[pd.DataFrame, list[int], set[Any]]:
    """Áp dụng tuần tự các bước.

    Returns:
        (df mới, số dòng bị ảnh hưởng của từng bước, hợp các dòng bị ảnh hưởng theo index gốc).
    """
    validate_steps(steps)
    current = df
    per_step: list[int] = []
    affected: set[Any] = set()
    for step in steps:
        column = step.get("column")
        if column and column not in current.columns:
            raise RuleError(f"Cột “{column}” không tồn tại trong dữ liệu.")
        current, changed = _OPS[step["op"]](current, column, step.get("params") or {})
        per_step.append(len(changed))
        affected |= changed
    return current, per_step, affected


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {str(k): ("" if v is None else str(v)) for k, v in row.items()}
        for row in frame.to_dict("records")
    ]


def compute_preview(df: pd.DataFrame, steps: list[dict[str, Any]], sample_rows: int) -> dict:
    """PreviewResult (thiếu version_id): before/after trên mẫu, diff từng ô, số dòng ảnh hưởng."""
    sample = df.head(sample_rows)
    after, _, affected = apply_steps(sample, steps)
    diffs = []
    shared_columns = [c for c in sample.columns if c in after.columns]
    for position, label in enumerate(sample.index):
        if label not in after.index:
            continue
        for column in shared_columns:
            before_value, after_value = sample.at[label, column], after.at[label, column]
            if str(before_value) != str(after_value):
                diffs.append(
                    {
                        "row_index": position,
                        "column": column,
                        "before": before_value,
                        "after": after_value,
                    }
                )
    return {
        "before_rows": _records(sample),
        "after_rows": _records(after),
        "diffs": diffs,
        "affected_row_count": len(affected),
    }
