"""Định nghĩa DSL (Domain Specific Language) cho rule làm sạch dữ liệu.

AI và người dùng chỉ được sinh ra rule ở dạng JSON tuân theo DSL này. Rule Engine
(app.services.rules.engine) là nơi DUY NHẤT thực thi rule trên dữ liệu thật bằng Pandas.
KHÔNG BAO GIỜ dùng eval()/exec() để chạy rule.

Mỗi RuleStep tương ứng một lời gọi op có chữ ký:
    (df: pd.DataFrame, column: str | None, params: dict) -> tuple[pd.DataFrame, int]
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Danh sách toàn bộ op hợp lệ mà Rule Engine hỗ trợ.
ALLOWED_OPS: set[str] = {
    "trim_whitespace",
    "change_case",
    "replace_values",
    "standardize_date",
    "standardize_phone",
    "standardize_email",
    "cast_type",
    "fill_missing",
    "drop_duplicates",
    "drop_rows_where",
    "flag_outliers",
    "rename_column",
    "drop_column",
}

# Các op không bắt buộc phải chỉ định "column" (áp dụng cho toàn bảng hoặc nhiều cột).
OPS_WITHOUT_REQUIRED_COLUMN: set[str] = {"drop_duplicates"}

RuleOpName = Literal[
    "trim_whitespace",
    "change_case",
    "replace_values",
    "standardize_date",
    "standardize_phone",
    "standardize_email",
    "cast_type",
    "fill_missing",
    "drop_duplicates",
    "drop_rows_where",
    "flag_outliers",
    "rename_column",
    "drop_column",
]


class RuleStep(BaseModel):
    """Một bước làm sạch dữ liệu: gọi một op cụ thể lên một cột (hoặc toàn bảng)."""

    op: RuleOpName
    column: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("op")
    @classmethod
    def validate_op(cls, value: str) -> str:
        """Chặn mọi op nằm ngoài danh sách ALLOWED_OPS (phòng AI sinh ra op lạ)."""
        if value not in ALLOWED_OPS:
            raise ValueError(f"Op '{value}' không được hỗ trợ bởi Rule Engine.")
        return value

    @model_validator(mode="after")
    def validate_column_required(self) -> "RuleStep":
        """Hầu hết op cần chỉ định cột áp dụng, trừ các op trong OPS_WITHOUT_REQUIRED_COLUMN."""
        if self.op not in OPS_WITHOUT_REQUIRED_COLUMN and not self.column:
            raise ValueError(f"Op '{self.op}' yêu cầu phải chỉ định 'column'.")
        return self


class RuleSet(BaseModel):
    """Một tập hợp các RuleStep được áp dụng tuần tự lên dataset."""

    steps: list[RuleStep] = Field(default_factory=list)


class RuleTemplateCreate(BaseModel):
    """Dữ liệu tạo rule template lưu trong project."""

    name: str = Field(min_length=1, max_length=255)
    rule_json: RuleSet


class RuleTemplateOut(BaseModel):
    """Rule template trả về cho client."""

    id: int
    project_id: int
    name: str
    rule_json: RuleSet
    created_by: int
