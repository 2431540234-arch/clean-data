"""Mapping tên cột tầng 2: dùng AI khi fuzzy matching (tầng 1) không tìm được cột phù hợp."""


def suggest_column_mapping_with_ai(
    unmatched_columns: list[str], known_schema: list[str]
) -> dict[str, str | None]:
    """Gợi ý mapping cho các cột chưa khớp được bằng fuzzy matching.

    Gợi ý cách làm: gọi app.services.ai.client.AIClient với prompt từ
    app.services.ai.prompts.build_mapping_prompt, validate kết quả trả về là
    dict[str, str | None] trước khi dùng.
    """
    raise NotImplementedError("TODO: gọi AI để gợi ý mapping cho các cột chưa khớp.")
