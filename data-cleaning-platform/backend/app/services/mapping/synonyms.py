"""Đọc và tra cứu từ điển đồng nghĩa tên cột (app/data/column_synonyms.json)."""

import json
from functools import lru_cache
from pathlib import Path

from app.services.mapping.normalizer import normalize_column_name

_SYNONYMS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "column_synonyms.json"


@lru_cache
def load_synonyms() -> dict[str, list[str]]:
    """Nạp từ điển đồng nghĩa từ app/data/column_synonyms.json.

    Cấu trúc: {"ten_cot_chuan": ["bien_the_1", "bien_the_2", ...], ...}
    """
    with open(_SYNONYMS_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def _index() -> dict[str, str]:
    """Tên đã chuẩn hóa (của tên chuẩn lẫn mọi biến thể) -> tên chuẩn."""
    index: dict[str, str] = {}
    for canonical, variants in load_synonyms().items():
        for name in [canonical, *variants]:
            index.setdefault(normalize_column_name(name), canonical)
    return index


def find_canonical_name(normalized_name: str) -> str | None:
    """Tên cột chuẩn ứng với một tên cột đã chuẩn hóa theo từ điển đồng nghĩa, hoặc None."""
    return _index().get(normalized_name)
