"""Các prompt template dùng khi gọi AI. AI chỉ được yêu cầu sinh JSON theo DSL rule."""

SUGGESTION_SYSTEM_PROMPT = """Bạn là chuyên gia làm sạch dữ liệu. Chỉ trả lời bằng JSON hợp lệ
theo đúng schema RuleSet được cung cấp. KHÔNG được sinh ra code Python, KHÔNG giải thích
bằng văn xuôi ngoài JSON, KHÔNG dùng bất kỳ op nào ngoài danh sách được cho phép."""


def build_suggestion_prompt(profiling_summary: dict) -> str:
    """Sinh prompt yêu cầu AI đề xuất RuleSet dựa trên kết quả profiling.

    Gợi ý cách làm: nhúng profiling_summary (dạng JSON) và danh sách ALLOWED_OPS
    (từ app.schemas.rule) vào prompt, yêu cầu AI trả về JSON RuleSet kèm explanation.
    """
    raise NotImplementedError("TODO: dựng prompt sinh gợi ý rule từ profiling_summary.")


def build_explanation_prompt(issue_summary: dict) -> str:
    """Sinh prompt yêu cầu AI giải thích một lỗi dữ liệu bằng tiếng Việt dễ hiểu."""
    raise NotImplementedError("TODO: dựng prompt giải thích lỗi bằng tiếng Việt.")


def build_mapping_prompt(unmatched_columns: list[str], known_schema: list[str]) -> str:
    """Sinh prompt yêu cầu AI gợi ý mapping cột (tầng 2, sau khi fuzzy match thất bại)."""
    raise NotImplementedError("TODO: dựng prompt mapping cột tầng 2 bằng AI.")
