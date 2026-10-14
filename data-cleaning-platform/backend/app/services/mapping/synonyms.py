"""Đọc và tra cứu từ điển đồng nghĩa tên cột (app/data/column_synonyms.json)."""

import json
from functools import lru_cache
from pathlib import Path

_SYNONYMS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "column_synonyms.json"


@lru_cache
def load_synonyms() -> dict[str, list[str]]:
    """Nạp từ điển đồng nghĩa từ app/data/column_synonyms.json.

    Cấu trúc: {"ten_cot_chuan": ["bien_the_1", "bien_the_2", ...], ...}
    """
    with open(_SYNONYMS_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_canonical_name(normalized_name: str) -> str | None:
    """Tìm tên cột chuẩn tương ứng với một tên cột đã chuẩn hóa, dựa trên từ điển đồng nghĩa.

    Gợi ý cách làm: duyệt load_synonyms(), nếu normalized_name khớp với bất kỳ biến thể
    nào (hoặc chính là key) thì trả về key đó; nếu không tìm thấy trả về None.
    """
    raise NotImplementedError("TODO: tra cứu normalized_name trong từ điển đồng nghĩa.")
