"""Logic thuần của bước Mapping cột: đọc schema chuẩn, kiểm tra tên trùng, dựng rule rename_column.

Tách khỏi giao diện để kiểm thử trực tiếp. Rule sinh ra theo đúng DSL của backend
(`app/schemas/rule.py`: op "rename_column", column = tên cũ, params.new_name = tên mới).
"""

import re

KEEP = "(giữ nguyên)"  # lựa chọn "không đổi tên cột này"
_MAX_NAME_LENGTH = 255
_SPLIT_RE = re.compile(r"[\n,;]+")


def parse_target_schema(text: str) -> tuple[list[str], list[str]]:
    """Tách danh sách cột chuẩn (mỗi dòng một cột, hoặc phân cách bằng , ;).

    Returns:
        (danh sách cột đã bỏ trống/trùng, danh sách thông báo lỗi tiếng Việt).
    """
    names: list[str] = []
    for part in _SPLIT_RE.split(text):
        name = part.strip()
        if name and name not in names:
            names.append(name)
    problems = []
    if not names:
        problems.append("Vui lòng nhập ít nhất một cột chuẩn.")
    too_long = [n for n in names if len(n) > _MAX_NAME_LENGTH]
    if too_long:
        problems.append(f"Tên cột tối đa {_MAX_NAME_LENGTH} ký tự.")
    return names, problems


def final_names(sources: list[str], choices: list[str]) -> list[str]:
    """Tên cột sau khi áp dụng lựa chọn (KEEP giữ nguyên tên gốc)."""
    return [
        source if choice == KEEP else choice
        for source, choice in zip(sources, choices, strict=True)
    ]


def duplicate_names(sources: list[str], choices: list[str]) -> list[str]:
    """Các tên xuất hiện từ 2 cột trở lên sau khi đổi (không cho phép vì làm mất dữ liệu)."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in final_names(sources, choices):
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    return duplicates


def build_rename_steps(sources: list[str], choices: list[str]) -> list[dict]:
    """RuleStep rename_column cho các cột thực sự đổi tên (bỏ KEEP và đổi sang chính nó)."""
    return [
        {"op": "rename_column", "column": source, "params": {"new_name": choice}}
        for source, choice in zip(sources, choices, strict=True)
        if choice != KEEP and choice != source
    ]
