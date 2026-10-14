"""Test thật cho Rule Engine: áp dụng rule trim_whitespace, dry_run không ảnh hưởng dữ liệu gốc."""

import pandas as pd
import pytest

from app.schemas.rule import RuleSet
from app.services.rules.engine import apply_rules, dry_run
from app.services.rules.registry import get_op


def test_apply_rules_trim_whitespace() -> None:
    """apply_rules phải xóa khoảng trắng dư và đếm đúng số dòng bị ảnh hưởng."""
    df = pd.DataFrame({"ten": ["  An  ", "Binh", " Chi"]})
    rule_set = RuleSet.model_validate({"steps": [{"op": "trim_whitespace", "column": "ten"}]})

    result_df, step_results = apply_rules(df, rule_set)

    assert result_df["ten"].tolist() == ["An", "Binh", "Chi"]
    assert len(step_results) == 1
    assert step_results[0].affected_rows == 2


def test_dry_run_does_not_mutate_original_dataframe() -> None:
    """dry_run phải trả về DataFrame mới, không sửa DataFrame gốc truyền vào."""
    df = pd.DataFrame({"ten": ["  An  "]})
    rule_set = RuleSet.model_validate({"steps": [{"op": "trim_whitespace", "column": "ten"}]})

    result_df, _ = dry_run(df, rule_set)

    assert df["ten"].tolist() == ["  An  "]
    assert result_df["ten"].tolist() == ["An"]


def test_get_op_unknown_raises_key_error() -> None:
    """get_op phải raise KeyError khi tên op chưa được đăng ký trong registry."""
    with pytest.raises(KeyError):
        get_op("op_khong_ton_tai")


def test_rule_set_rejects_disallowed_op() -> None:
    """RuleSet phải từ chối op không thuộc DSL (phòng AI sinh ra op lạ ngoài danh sách)."""
    with pytest.raises(ValueError):
        RuleSet.model_validate({"steps": [{"op": "exec_python_code", "column": "ten"}]})
