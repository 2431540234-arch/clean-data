"""Mapping tên cột tầng 2: dùng AI khi fuzzy matching (tầng 1) không tìm được cột phù hợp."""

from sqlalchemy.orm import Session

from app.services.ai.prompts import MAPPING_SYSTEM_PROMPT, build_mapping_prompt
from app.services.ai.service import call_ai


def suggest_column_mapping_with_ai(
    db: Session,
    user_id: int | None,
    unmatched_columns: list[str],
    known_schema: list[str],
) -> dict[str, str | None]:
    """Gợi ý mapping cho các cột chưa khớp được bằng quy tắc; chỉ gửi TÊN cột, không gửi dữ liệu.

    Trả {} khi AI không dùng được. Kết quả được lọc chặt: chỉ nhận cột nguồn đã hỏi, cột đích phải
    nằm trong known_schema, và mỗi cột đích chỉ dùng một lần.
    """
    if not unmatched_columns or not known_schema:
        return {}
    data = call_ai(
        db,
        user_id,
        "column_mapping",
        MAPPING_SYSTEM_PROMPT,
        build_mapping_prompt(unmatched_columns, known_schema),
    )
    raw = data.get("mapping") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return {}
    allowed_targets = set(known_schema)
    result: dict[str, str | None] = {}
    used: set[str] = set()
    for source in unmatched_columns:
        target = raw.get(source)
        if isinstance(target, str) and target in allowed_targets and target not in used:
            result[source] = target
            used.add(target)
    return result
