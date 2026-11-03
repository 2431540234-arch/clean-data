"""Rule Engine: thực thi tuần tự các RuleStep lên một DataFrame bằng Pandas.

Đây là nơi DUY NHẤT trong hệ thống được phép sửa dữ liệu thật dựa trên rule JSON.
AI và API chỉ sinh/nhận RuleSet (JSON đã được validate bởi app.schemas.rule), KHÔNG
BAO GIỜ dùng eval()/exec() để chạy logic do AI sinh ra.
"""

import pandas as pd

from app.schemas.rule import RuleSet, RuleStep

# Import các module ops để chúng tự đăng ký vào registry (OPS) qua decorator @register.
from app.services.rules import ops  # noqa: F401
from app.services.rules.registry import RuleError, get_op

MAX_STEPS = 50  # chặn RuleSet khổng lồ (do lỗi hoặc cố ý) làm treo máy chủ


class RuleStepResult:
    """Kết quả thực thi một RuleStep: số dòng bị ảnh hưởng."""

    def __init__(self, step: RuleStep, affected_rows: int) -> None:
        self.step = step
        self.affected_rows = affected_rows


def validate_rule_set(rule_set: RuleSet) -> None:
    """Kiểm tra RuleSet có thể thực thi: có bước, không quá nhiều bước."""
    if not rule_set.steps:
        raise RuleError("Không có bước nào để áp dụng.")
    if len(rule_set.steps) > MAX_STEPS:
        raise RuleError(f"Một lần áp dụng tối đa {MAX_STEPS} bước.")


def apply_rules(df: pd.DataFrame, rule_set: RuleSet) -> tuple[pd.DataFrame, list[RuleStepResult]]:
    """Áp dụng tuần tự từng RuleStep trong rule_set lên df, trả về df mới và kết quả từng bước.

    Args:
        df: DataFrame gốc, không bị sửa trực tiếp (mỗi op trả về DataFrame mới).
        rule_set: tập hợp các bước làm sạch đã được validate theo DSL.

    Returns:
        Tuple (DataFrame sau khi áp dụng toàn bộ rule, danh sách kết quả từng bước).

    Raises:
        RuleError: rule không thực thi được (cột không tồn tại, tham số sai...); thông báo tiếng
            Việt, và không có thay đổi nào được giữ lại vì df gốc không bị sửa.
    """
    validate_rule_set(rule_set)
    result_df = df
    step_results: list[RuleStepResult] = []

    for number, step in enumerate(rule_set.steps, start=1):
        try:
            op_func = get_op(step.op)
        except KeyError as exc:
            raise RuleError(f"Bước {number}: op “{step.op}” chưa được hỗ trợ.") from exc
        try:
            result_df, affected_rows = op_func(result_df, step.column, step.params)
        except RuleError as exc:
            raise RuleError(f"Bước {number} ({step.op}): {exc}") from exc
        step_results.append(RuleStepResult(step=step, affected_rows=affected_rows))

    return result_df, step_results


def dry_run(df: pd.DataFrame, rule_set: RuleSet) -> tuple[pd.DataFrame, list[RuleStepResult]]:
    """Chạy thử rule_set trên một bản sao của df, không ảnh hưởng tới dữ liệu gốc.

    Dùng cho chức năng preview (xem trước trước/sau khi chưa xác nhận áp dụng).
    """
    return apply_rules(df.copy(deep=True), rule_set)


def changed_row_labels(before: pd.DataFrame, after: pd.DataFrame) -> set:
    """Nhãn các dòng bị tác động: dòng bị xóa, dòng đổi giá trị ở cột có cả trước và sau, và
    dòng được đánh dấu "True" ở cột mới (flag_outliers)."""
    labels = set(before.index.difference(after.index))
    kept = before.index.intersection(after.index)
    for column in before.columns:
        if column not in after.columns:
            continue
        old = before.loc[kept, column].astype(str)
        new = after.loc[kept, column].astype(str)
        labels.update(kept[(old != new).to_numpy()])
    for column in after.columns.difference(before.columns):
        flagged = after[column].astype(str) == "True"
        labels.update(after.index[flagged.to_numpy()])
    return labels
