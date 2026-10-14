"""Định nghĩa DSL (Domain Specific Language) cho rule làm sạch dữ liệu.

AI và người dùng chỉ được sinh ra rule ở dạng JSON tuân theo DSL này. Rule Engine
(app.services.rules.engine) là nơi DUY NHẤT thực thi rule trên dữ liệu thật bằng Pandas.
KHÔNG BAO GIỜ dùng eval()/exec() để chạy rule.

Mỗi RuleStep tương ứng một lời gọi op có chữ ký:
    (df: pd.DataFrame, column: str | None, params: dict) -> tuple[pd.DataFrame, int]
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

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


RULESET_TYPE = "ruleset"


def rule_set_to_columns(rule_set: RuleSet) -> dict[str, Any]:
    """Chuyển RuleSet thành các cột của bảng rules: rule_type, target_column, params.

    Một bước: rule_type = op, target_column = column, params = params của bước.
    Còn lại (0 hoặc nhiều bước): rule_type = 'ruleset', params = toàn bộ RuleSet.
    """
    if len(rule_set.steps) == 1:
        step = rule_set.steps[0]
        return {"rule_type": step.op, "target_column": step.column, "params": step.params}
    return {
        "rule_type": RULESET_TYPE,
        "target_column": None,
        "params": rule_set.model_dump(mode="json"),
    }


def columns_to_rule_set(
    rule_type: str, target_column: str | None, params: dict[str, Any]
) -> RuleSet:
    """Dựng lại RuleSet từ các cột rule_type/target_column/params (nghịch đảo của hàm trên)."""
    if rule_type == RULESET_TYPE:
        return RuleSet.model_validate(params)
    return RuleSet.model_validate(
        {"steps": [{"op": rule_type, "column": target_column, "params": params}]}
    )


class RuleTemplateCreate(BaseModel):
    """Dữ liệu tạo rule template lưu trong project; client gửi RuleSet, server tự tách cột."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rule_set: RuleSet


class RuleTemplateOut(BaseModel):
    """Rule template trả về cho client (rule_set dựng lại từ rule_type/target_column/params)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int | None
    name: str
    description: str | None
    rule_type: str
    target_column: str | None
    params: dict[str, Any]
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def rule_set(self) -> RuleSet:
        """RuleSet đầy đủ để client/rule engine dùng trực tiếp."""
        return columns_to_rule_set(self.rule_type, self.target_column, self.params)
