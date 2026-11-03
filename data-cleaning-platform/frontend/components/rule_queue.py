"""Helpers giữ hàng đợi rule và bản xem trước nhất quán giữa các nguồn."""

import json
from typing import Any


def normalize_queue(queue: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Đưa hàng đợi cũ (danh sách RuleStep) về dạng entry có nguồn và bước DSL."""
    entries = []
    for item in queue or []:
        if not isinstance(item, dict):
            raise ValueError("Hàng đợi quy tắc phải chứa các đối tượng.")
        if isinstance(item.get("step"), dict):
            entry = dict(item)
            entry["step"] = dict(item["step"])
            entry.setdefault("source", "manual")
            entries.append(entry)
        elif isinstance(item.get("op"), str):
            entries.append({"step": dict(item), "source": "manual"})
        else:
            raise ValueError("Bước trong hàng đợi không đúng cấu trúc RuleStep.")
    return entries


def queue_steps(queue: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Lấy các RuleStep theo thứ tự thực thi."""
    return [entry["step"] for entry in normalize_queue(queue)]


def add_queue_steps(
    queue: list[dict[str, Any]] | None,
    steps: list[dict[str, Any]],
    *,
    source: str = "manual",
) -> list[dict[str, Any]]:
    """Thêm các bước vào cuối hàng đợi."""
    entries = normalize_queue(queue)
    entries.extend({"step": dict(step), "source": source} for step in steps)
    return entries


def sync_accepted_suggestions(
    queue: list[dict[str, Any]] | None, suggestions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Đồng bộ bước từ gợi ý đã chấp nhận nhưng giữ nguyên thứ tự người dùng đã xếp."""
    entries = normalize_queue(queue)
    accepted = {item["id"]: item for item in suggestions if item.get("status") == "accepted"}
    entries = [
        entry
        for entry in entries
        if entry.get("source") != "suggestion" or entry.get("suggestion_id") in accepted
    ]
    present = {
        (entry.get("suggestion_id"), entry.get("step_index"))
        for entry in entries
        if entry.get("source") == "suggestion"
    }

    for suggestion_id, suggestion in accepted.items():
        for step_index, step in enumerate(suggestion["proposed_rule"]["steps"]):
            if (suggestion_id, step_index) in present:
                continue
            entries.append(
                {
                    "step": dict(step),
                    "source": "suggestion",
                    "suggestion_id": suggestion_id,
                    "step_index": step_index,
                }
            )
    return entries


def queue_signature(steps: list[dict[str, Any]]) -> str:
    """Tạo chữ ký ổn định cho đúng thứ tự và nội dung rule được xem trước."""
    return json.dumps(steps, sort_keys=True, ensure_ascii=False)


def preview_is_current(
    preview: dict[str, Any] | None,
    version_id: int,
    steps: list[dict[str, Any]],
) -> bool:
    """Chỉ mở áp dụng khi preview thuộc version và đúng hàng đợi hiện tại."""
    return bool(
        preview
        and steps
        and preview.get("version_id") == version_id
        and preview.get("signature") == queue_signature(steps)
        and isinstance(preview.get("result"), dict)
    )
