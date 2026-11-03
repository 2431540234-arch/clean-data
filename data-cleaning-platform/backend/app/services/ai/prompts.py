"""Các prompt template dùng khi gọi AI. AI chỉ được yêu cầu sinh JSON theo DSL rule."""

import json
from typing import Any

SUGGESTION_SYSTEM_PROMPT = """Bạn là chuyên gia làm sạch dữ liệu. Chỉ trả lời bằng JSON hợp lệ
theo đúng schema được cung cấp. KHÔNG được sinh ra code Python, KHÔNG giải thích
bằng văn xuôi ngoài JSON, KHÔNG dùng bất kỳ op nào ngoài danh sách được cho phép.
Dữ liệu người dùng đã được che bớt thông tin cá nhân; không cố đoán phần bị che."""

# Op AI được phép đề xuất: bỏ drop_column và drop_rows_where vì làm mất dữ liệu không hoàn tác được
# ngay trong một bước (người dùng vẫn tự tạo hai op này trong trình dựng rule).
AI_ALLOWED_OPS: tuple[str, ...] = (
    "trim_whitespace",
    "change_case",
    "replace_values",
    "standardize_date",
    "standardize_phone",
    "standardize_email",
    "cast_type",
    "fill_missing",
    "drop_duplicates",
    "flag_outliers",
    "rename_column",
)

OPS_GUIDE = """Các op và params:
- trim_whitespace: {} (cắt khoảng trắng đầu/cuối, gộp khoảng trắng thừa)
- change_case: {"mode": "upper"|"lower"|"title"|"capitalize"}
- replace_values: {"mapping": {"giá trị cũ": "giá trị mới"}}
- standardize_date: {"output_format": "%Y-%m-%d", "dayfirst": true}
- standardize_phone: {"region": "VN", "output_format": "E164"|"NATIONAL"|"INTERNATIONAL"}
- standardize_email: {"drop_invalid": false}
- cast_type: {"target_type": "int"|"float"|"str", "on_error": "coerce"|"raise"}
- fill_missing: {"strategy": "constant"|"mean"|"median"|"mode"|"ffill"|"bfill", "value": "..."}
- drop_duplicates: {"subset": ["cột"] hoặc null, "keep": "first"|"last"} (column có thể bỏ trống)
- flag_outliers: {"method": "iqr"|"zscore", "threshold": số}
- rename_column: {"new_name": "tên mới"}"""


def build_suggestion_prompt(profiling_summary: dict[str, Any]) -> str:
    """Prompt yêu cầu AI đề xuất thêm các RuleSet làm sạch dựa trên tóm tắt profiling."""
    return f"""Dưới đây là tóm tắt dữ liệu (đã che thông tin cá nhân) và các lỗi đã phát hiện:
{json.dumps(profiling_summary, ensure_ascii=False)}

{OPS_GUIDE}

Hãy đề xuất tối đa 8 gợi ý làm sạch dựa trên ĐÚNG các cột và lỗi ở trên. Mỗi gợi ý gồm 1-3 bước.
Chỉ dùng op trong danh sách: {", ".join(AI_ALLOWED_OPS)}. "column" phải là tên cột có thật.
Trả về JSON đúng dạng:
{{"suggestions": [{{"issue_id": <id lỗi liên quan hoặc null>, "column": "<cột chính>",
"explanation": "<giải thích tiếng Việt 1-2 câu cho người không chuyên>", "confidence": <0..1>,
"rule": {{"steps": [{{"op": "...", "column": "...", "params": {{}}}}]}}}}]}}"""


def build_explanation_prompt(issue_summary: dict[str, Any]) -> str:
    """Prompt yêu cầu AI giải thích một lỗi dữ liệu bằng tiếng Việt dễ hiểu."""
    return (
        "Giải thích ngắn gọn (1-2 câu, tiếng Việt, cho người không chuyên) lỗi dữ liệu sau và "
        'ảnh hưởng của nó. Trả về JSON {"explanation": "..."}.\n'
        f"{json.dumps(issue_summary, ensure_ascii=False)}"
    )


MAPPING_SYSTEM_PROMPT = """Bạn ghép tên cột của một file dữ liệu vào bộ cột chuẩn. Chỉ trả lời
bằng JSON hợp lệ. Chỉ ghép khi chắc chắn về ý nghĩa; không chắc thì để null."""


def build_mapping_prompt(unmatched_columns: list[str], known_schema: list[str]) -> str:
    """Prompt mapping cột tầng 2 (sau khi so khớp bằng quy tắc không ra). Chỉ gửi tên cột."""
    return f"""Cột cần ghép: {json.dumps(unmatched_columns, ensure_ascii=False)}
Bộ cột chuẩn: {json.dumps(known_schema, ensure_ascii=False)}
Mỗi cột chuẩn chỉ được dùng cho tối đa một cột. Trả về JSON dạng
{{"mapping": {{"<cột cần ghép>": "<cột chuẩn hoặc null>"}}}}."""
