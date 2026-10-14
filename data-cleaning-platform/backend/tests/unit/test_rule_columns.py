"""Test chuyển đổi RuleSet <-> các cột rule_type/target_column/params của bảng rules."""

from app.schemas.rule import (
    RuleSet,
    RuleTemplateCreate,
    columns_to_rule_set,
    rule_set_to_columns,
)


def test_single_step_maps_to_op_column_params() -> None:
    rule_set = RuleSet.model_validate(
        {"steps": [{"op": "change_case", "column": "name", "params": {"mode": "upper"}}]}
    )
    cols = rule_set_to_columns(rule_set)
    assert cols == {
        "rule_type": "change_case",
        "target_column": "name",
        "params": {"mode": "upper"},
    }
    assert columns_to_rule_set(**cols) == rule_set


def test_multi_step_and_empty_use_ruleset_type() -> None:
    multi = RuleSet.model_validate(
        {"steps": [{"op": "trim_whitespace", "column": "a"}, {"op": "drop_duplicates"}]}
    )
    cols = rule_set_to_columns(multi)
    assert cols["rule_type"] == "ruleset"
    assert cols["target_column"] is None
    assert columns_to_rule_set(**cols) == multi

    empty = RuleSet(steps=[])
    assert rule_set_to_columns(empty)["rule_type"] == "ruleset"
    assert columns_to_rule_set(**rule_set_to_columns(empty)) == empty


def test_template_create_accepts_rule_set() -> None:
    payload = RuleTemplateCreate.model_validate(
        {
            "name": "Chuẩn hóa email",
            "rule_set": {"steps": [{"op": "standardize_email", "column": "e"}]},
        }
    )
    assert payload.rule_set.steps[0].op == "standardize_email"
