"""Các op xử lý văn bản: trim_whitespace, change_case, replace_values."""

import re
from typing import Any

import pandas as pd

from app.services.rules.ops.common import map_cells, require_choice, require_column
from app.services.rules.registry import RuleError, register

_INNER_SPACES_RE = re.compile(r"[ \t ]+")
_WORD_RE = re.compile(r"\S+")
CASE_MODES = ("upper", "lower", "title", "capitalize")


@register("trim_whitespace")
def trim_whitespace(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Cắt khoảng trắng đầu/cuối và gộp các khoảng trắng liền nhau ở giữa thành một.

    Chỉ gộp dấu cách, tab và khoảng trắng không ngắt dòng; xuống dòng trong ô được giữ nguyên.
    """
    require_column(df, column)
    return map_cells(df, column, lambda s: _INNER_SPACES_RE.sub(" ", s.strip()))


def _title(text: str) -> str:
    return _WORD_RE.sub(lambda m: m.group()[:1].upper() + m.group()[1:].lower(), text)


@register("change_case")
def change_case(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Đổi hoa/thường. params.mode: upper | lower | title (Mỗi Từ) | capitalize (Chỉ chữ đầu)."""
    require_column(df, column)
    mode = require_choice(params, "mode", CASE_MODES, None)
    funcs = {
        "upper": str.upper,
        "lower": str.lower,
        "title": _title,
        "capitalize": lambda s: s[:1].upper() + s[1:].lower(),
    }
    return map_cells(df, column, funcs[mode])


@register("replace_values")
def replace_values(
    df: pd.DataFrame, column: str | None, params: dict[str, Any]
) -> tuple[pd.DataFrame, int]:
    """Thay các giá trị cụ thể theo params.mapping (giá trị cũ -> giá trị mới).

    So khớp nguyên văn; nếu không khớp thì thử lại với giá trị đã cắt khoảng trắng hai đầu. Áp
    cho mọi ô có giá trị (kể cả "N/A", "-") nên dùng được để đổi các dấu thay thế thành ô trống.
    """
    require_column(df, column)
    mapping = params.get("mapping")
    if not isinstance(mapping, dict) or not mapping:
        raise RuleError("Tham số mapping phải là một từ điển giá trị cũ -> giá trị mới.")
    table = {str(k): "" if v is None else str(v) for k, v in mapping.items()}

    def convert(text: str) -> str:
        if text in table:
            return table[text]
        return table.get(text.strip(), text)

    return map_cells(df, column, convert, skip_null=False)
