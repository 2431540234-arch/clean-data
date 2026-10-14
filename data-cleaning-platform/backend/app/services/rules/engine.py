"""Rule Engine: thực thi tuần tự các RuleStep lên một DataFrame bằng Pandas.

Đây là nơi DUY NHẤT trong hệ thống được phép sửa dữ liệu thật dựa trên rule JSON.
AI và API chỉ sinh/nhận RuleSet (JSON đã được validate bởi app.schemas.rule), KHÔNG
BAO GIỜ dùng eval()/exec() để chạy logic do AI sinh ra.
"""

import pandas as pd

from app.schemas.rule import RuleSet, RuleStep

# Import các module ops để chúng tự đăng ký vào registry (OPS) qua decorator @register.
from app.services.rules import ops  # noqa: F401
from app.services.rules.registry import get_op


class RuleStepResult:
    """Kết quả thực thi một RuleStep: số dòng bị ảnh hưởng."""

    def __init__(self, step: RuleStep, affected_rows: int) -> None:
        self.step = step
        self.affected_rows = affected_rows


def apply_rules(df: pd.DataFrame, rule_set: RuleSet) -> tuple[pd.DataFrame, list[RuleStepResult]]:
    """Áp dụng tuần tự từng RuleStep trong rule_set lên df, trả về df mới và kết quả từng bước.

    Args:
        df: DataFrame gốc, không bị sửa trực tiếp (mỗi op trả về DataFrame mới).
        rule_set: tập hợp các bước làm sạch đã được validate theo DSL.

    Returns:
        Tuple (DataFrame sau khi áp dụng toàn bộ rule, danh sách kết quả từng bước).
    """
    result_df = df
    step_results: list[RuleStepResult] = []

    for step in rule_set.steps:
        op_func = get_op(step.op)
        result_df, affected_rows = op_func(result_df, step.column, step.params)
        step_results.append(RuleStepResult(step=step, affected_rows=affected_rows))

    return result_df, step_results


def dry_run(df: pd.DataFrame, rule_set: RuleSet) -> tuple[pd.DataFrame, list[RuleStepResult]]:
    """Chạy thử rule_set trên một bản sao của df, không ảnh hưởng tới dữ liệu gốc.

    Dùng cho chức năng preview (xem trước trước/sau khi chưa xác nhận áp dụng).
    """
    return apply_rules(df.copy(deep=True), rule_set)
