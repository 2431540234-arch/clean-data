# Đặc tả DSL Rule làm sạch dữ liệu

> Nguyên tắc cốt lõi: AI và người dùng chỉ sinh ra **JSON** theo DSL này. Rule Engine
> (`app.services.rules.engine`) là nơi duy nhất thực thi, dùng Pandas, KHÔNG dùng eval()/exec().

## 1. Cấu trúc RuleSet

```json
{
  "steps": [
    {"op": "trim_whitespace", "column": "ho_ten", "params": {}},
    {"op": "standardize_date", "column": "ngay_sinh", "params": {"output_format": "%Y-%m-%d", "dayfirst": true}}
  ]
}
```

Xem định nghĩa Pydantic đầy đủ tại `backend/app/schemas/rule.py`.

## 2. Danh sách op được hỗ trợ

> TODO: với mỗi op, viết ví dụ input/output cụ thể.

| Op | Yêu cầu `column` | `params` chính |
|---|---|---|
| `trim_whitespace` | Có | — |
| `change_case` | Có | `mode` |
| `replace_values` | Có | `mapping` |
| `standardize_date` | Có | `output_format`, `dayfirst` |
| `standardize_phone` | Có | `region`, `output_format` |
| `standardize_email` | Có | `drop_invalid` |
| `cast_type` | Có | `target_type`, `on_error` |
| `fill_missing` | Có | `strategy`, `value` |
| `drop_duplicates` | Không | `subset`, `keep` |
| `drop_rows_where` | Có | `operator`, `value` |
| `flag_outliers` | Có | `method`, `threshold` |
| `rename_column` | Có | `new_name` |
| `drop_column` | Có | — |

## 3. Chữ ký hàm op

```python
def op_func(df: pd.DataFrame, column: str | None, params: dict) -> tuple[pd.DataFrame, int]:
    ...
```

Trả về DataFrame mới và số dòng bị ảnh hưởng (affected rows).

## 4. Lớp bảo vệ (validation)

1. `app.schemas.rule.RuleStep` — chặn op ngoài `ALLOWED_OPS`, bắt buộc `column` khi cần.
2. `app.services.ai.validator.validate_ai_rule_json` — validate JSON thô do AI trả về.
3. `app.services.rules.registry` — registry pattern, chỉ chạy được op đã đăng ký.

## 5. TODO

- Mô tả chi tiết hành vi edge-case của từng op (giá trị null, kiểu dữ liệu không khớp...).
- Quy ước versioning khi DSL thay đổi (thêm op mới có breaking không?).
