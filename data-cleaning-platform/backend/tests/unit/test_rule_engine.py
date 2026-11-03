"""Rule Engine: 13 op, xử lý ô thiếu, lỗi tham số, tính bất biến của dữ liệu đầu vào."""

import pandas as pd
import pytest

from app.schemas.rule import RuleSet
from app.services.rules.engine import MAX_STEPS, apply_rules, changed_row_labels, dry_run
from app.services.rules.registry import OPS, RuleError


def frame(**columns) -> pd.DataFrame:
    return pd.DataFrame({k: list(v) for k, v in columns.items()}, dtype=str)


def run(df, op, column=None, **params):
    """Chạy một op qua engine; trả (df mới, số dòng ảnh hưởng)."""
    result, steps = apply_rules(
        df, RuleSet.model_validate({"steps": [{"op": op, "column": column, "params": params}]})
    )
    return result, steps[0].affected_rows


def test_all_thirteen_ops_registered():
    from app.schemas.rule import ALLOWED_OPS

    assert set(OPS) == ALLOWED_OPS and len(OPS) == 13


# ---------------------------------------------------------------- trim / case / replace


def test_trim_strips_and_collapses_inner_spaces_but_keeps_newlines():
    df = frame(a=["  An  Bình ", "ok", "", "N/A", "x\ny"])
    result, affected = run(df, "trim_whitespace", "a")
    assert list(result["a"]) == ["An Bình", "ok", "", "N/A", "x\ny"] and affected == 1


def test_input_dataframe_is_never_modified():
    df = frame(a=[" x "])
    run(df, "trim_whitespace", "a")
    assert df["a"][0] == " x "


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("upper", ["NGUYỄN VĂN AN", "HÀ NỘI"]),
        ("lower", ["nguyễn văn an", "hà nội"]),
        ("title", ["Nguyễn Văn An", "Hà Nội"]),
        ("capitalize", ["Nguyễn văn an", "Hà nội"]),
    ],
)
def test_change_case_modes(mode, expected):
    df = frame(a=["nGUYỄN vĂN aN", "hÀ NỘI"])
    assert list(run(df, "change_case", "a", mode=mode)[0]["a"]) == expected


def test_change_case_errors_and_empty_cells():
    df = frame(a=["abc", "", "N/A"])
    with pytest.raises(RuleError, match="mode"):
        run(df, "change_case", "a", mode="rainbow")
    with pytest.raises(RuleError):
        run(df, "change_case", "a")
    assert list(run(df, "change_case", "a", mode="upper")[0]["a"]) == ["ABC", "", "N/A"]


def test_replace_values_exact_then_stripped_and_applies_to_null_tokens():
    df = frame(a=["HCM", " HCM ", "N/A", "Hà Nội", ""])
    result, affected = run(df, "replace_values", "a", mapping={"HCM": "TP. Hồ Chí Minh", "N/A": ""})
    assert list(result["a"]) == ["TP. Hồ Chí Minh", "TP. Hồ Chí Minh", "", "Hà Nội", ""]
    assert affected == 3


@pytest.mark.parametrize("mapping", [None, {}, "x", ["a"]])
def test_replace_values_requires_mapping(mapping):
    with pytest.raises(RuleError, match="mapping"):
        run(frame(a=["x"]), "replace_values", "a", mapping=mapping)


# ---------------------------------------------------------------- ngày, SĐT, email


def test_standardize_date_dayfirst_and_formats():
    df = frame(d=["15/04/1990", "1995-03-12", "03/04/2020", "31/02/2020", "abc", "", "N/A"])
    result, affected = run(df, "standardize_date", "d")
    assert list(result["d"]) == [
        "1990-04-15",
        "1995-03-12",
        "2020-04-03",
        "31/02/2020",  # không phải ngày thật: giữ nguyên
        "abc",
        "",
        "N/A",
    ]
    assert affected == 2  # "1995-03-12" đã đúng chuẩn nên không tính là thay đổi
    month_first, _ = run(df, "standardize_date", "d", dayfirst=False)
    assert month_first["d"][2] == "2020-03-04" and month_first["d"][0] == "1990-04-15"
    custom, _ = run(df, "standardize_date", "d", output_format="%d.%m.%Y")
    assert custom["d"][0] == "15.04.1990"


@pytest.mark.parametrize("fmt", ["", "yyyy", 5])
def test_standardize_date_rejects_bad_output_format(fmt):
    with pytest.raises(RuleError, match="output_format"):
        run(frame(d=["1/1/2000"]), "standardize_date", "d", output_format=fmt)


def test_standardize_phone_formats_and_invalid_kept():
    df = frame(p=["0901234567", "+84 933 445 566", "090-555-1234", "12345", "", "N/A"])
    e164, affected = run(df, "standardize_phone", "p", output_format="E164")
    assert list(e164["p"]) == [
        "+84901234567",
        "+84933445566",
        "+84905551234",
        "12345",
        "",
        "N/A",
    ]
    assert affected == 3
    national, _ = run(df, "standardize_phone", "p", output_format="NATIONAL")
    assert list(national["p"])[:3] == ["0901234567", "0933445566", "0905551234"]
    international, _ = run(df, "standardize_phone", "p", output_format="INTERNATIONAL")
    assert international["p"][0] == "+84 901 234 567"
    with pytest.raises(RuleError):
        run(df, "standardize_phone", "p", output_format="XYZ")
    with pytest.raises(RuleError, match="Mã vùng"):
        run(df, "standardize_phone", "p", region="ZZ")


def test_standardize_email_lowercases_and_optionally_drops_invalid():
    df = frame(e=[" A@X.VN ", "b@y.com", "bad@invalid", "", "N/A"])
    kept, affected = run(df, "standardize_email", "e")
    assert list(kept["e"]) == ["a@x.vn", "b@y.com", "bad@invalid", "", "N/A"] and affected == 1
    dropped, affected = run(df, "standardize_email", "e", drop_invalid=True)
    assert list(dropped["e"]) == ["a@x.vn", "b@y.com", "", "", "N/A"] and affected == 2


# ---------------------------------------------------------------- cast_type, fill_missing


def test_cast_type_int_float_str_and_coerce():
    df = frame(n=["29", " 30 ", "3,5", "abc", "N/A", "7.0", ""])
    as_int, affected = run(df, "cast_type", "n", target_type="int")
    assert list(as_int["n"]) == ["29", "30", "", "", "", "7", ""]
    assert affected == 5  # " 30 ", "3,5", "abc", "N/A", "7.0" đều đổi
    as_float, _ = run(df, "cast_type", "n", target_type="float")
    assert list(as_float["n"]) == ["29", "30", "3.5", "", "", "7", ""]
    as_str, _ = run(df, "cast_type", "n", target_type="str")
    assert as_str["n"][1] == "30"


def test_cast_type_raise_mode_and_bad_target():
    df = frame(n=["1", "x"])
    with pytest.raises(RuleError, match="không ép được"):
        run(df, "cast_type", "n", target_type="int", on_error="raise")
    with pytest.raises(RuleError):
        run(df, "cast_type", "n", target_type="date")
    with pytest.raises(RuleError):
        run(df, "cast_type", "n", target_type="int", on_error="explode")


@pytest.mark.parametrize(
    ("strategy", "extra", "values", "expected"),
    [
        (
            "constant",
            {"value": "Không rõ"},
            ["10", "", "30", "N/A", "20"],
            ["10", "Không rõ", "30", "Không rõ", "20"],
        ),
        ("mean", {}, ["10", "", "30", "N/A", "20"], ["10", "20", "30", "20", "20"]),
        ("median", {}, ["10", "", "30", "N/A", "20"], ["10", "20", "30", "20", "20"]),
        ("mode", {}, ["10", "", "30", "N/A", "10"], ["10", "10", "30", "10", "10"]),
        ("ffill", {}, ["10", "", "30", "N/A", "20"], ["10", "10", "30", "30", "20"]),
        ("bfill", {}, ["10", "", "30", "N/A", "20"], ["10", "30", "30", "20", "20"]),
    ],
)
def test_fill_missing_strategies(strategy, extra, values, expected):
    result, affected = run(frame(n=values), "fill_missing", "n", strategy=strategy, **extra)
    assert list(result["n"]) == expected and affected == 2


def test_fill_missing_edge_cases():
    df = frame(n=["", "5"])
    first, affected = run(df, "fill_missing", "n", strategy="ffill")
    assert list(first["n"]) == ["", "5"] and affected == 0  # không có gì để điền ở dòng đầu
    with pytest.raises(RuleError, match="value"):
        run(df, "fill_missing", "n", strategy="constant")
    with pytest.raises(RuleError, match="số"):
        run(frame(n=["a", ""]), "fill_missing", "n", strategy="mean")
    with pytest.raises(RuleError):
        run(frame(n=["", ""]), "fill_missing", "n", strategy="mode")
    with pytest.raises(RuleError, match="strategy"):
        run(df, "fill_missing", "n", strategy="magic")


# ---------------------------------------------------------------- dòng


def test_drop_duplicates_all_subset_keep():
    df = frame(a=["x", "y", "x", "x"], b=["1", "2", "1", "9"])
    result, affected = run(df, "drop_duplicates")
    assert list(result.index) == [0, 1, 3] and affected == 1
    last, _ = run(df, "drop_duplicates", subset=["a"], keep="last")
    assert list(last.index) == [1, 3]
    by_column, affected = run(df, "drop_duplicates", "a")
    assert affected == 2 and list(by_column.index) == [0, 1]
    with pytest.raises(RuleError):
        run(df, "drop_duplicates", subset=["khong_co"])
    with pytest.raises(RuleError):
        run(df, "drop_duplicates", subset=[])
    with pytest.raises(RuleError):
        run(df, "drop_duplicates", keep="middle")


@pytest.mark.parametrize(
    ("operator", "value", "dropped"),
    [
        ("gt", "30", [34, 150]),
        ("lt", "0", [-5]),
        ("gte", "150", [150]),
        ("lte", "-5", [-5]),
        ("eq", "29", [29]),
        ("neq", "29", [34, 150, -5]),
        ("is_null", None, ["null"]),
        ("is_not_null", None, [29, 34, 150, -5]),
    ],
)
def test_drop_rows_where_operators(operator, value, dropped):
    df = frame(t=["29", "34", "150", "-5", "N/A"])
    params = {"operator": operator}
    if value is not None:
        params["value"] = value
    result, affected = run(df, "drop_rows_where", "t", **params)
    kept = set(result["t"])
    expected_dropped = {"N/A" if d == "null" else str(d) for d in dropped}
    assert set(df["t"]) - kept == expected_dropped and affected == len(expected_dropped)


def test_drop_rows_where_errors_and_string_compare():
    df = frame(t=["a", "b"])
    with pytest.raises(RuleError, match="operator"):
        run(df, "drop_rows_where", "t", operator="like", value="a")
    with pytest.raises(RuleError, match="value"):
        run(df, "drop_rows_where", "t", operator="eq")
    result, affected = run(df, "drop_rows_where", "t", operator="eq", value="a")
    assert list(result["t"]) == ["b"] and affected == 1


def test_flag_outliers_iqr_and_zscore_add_column_without_changing_data():
    ages = ["29", "34", "37", "32", "26", "40", "31", "33", "150", "-5", "", "abc"]
    df = frame(tuoi=ages)
    result, affected = run(df, "flag_outliers", "tuoi")
    assert affected == 2 and list(result.columns) == ["tuoi", "tuoi_is_outlier"]
    assert list(result["tuoi"]) == ages  # dữ liệu gốc nguyên vẹn
    assert result["tuoi_is_outlier"][8] == "True" and result["tuoi_is_outlier"][0] == "False"
    assert result["tuoi_is_outlier"][10] == "False" and result["tuoi_is_outlier"][11] == "False"
    z, affected = run(df, "flag_outliers", "tuoi", method="zscore", threshold=2.5)
    assert affected >= 1 and z["tuoi_is_outlier"][8] == "True"
    tiny, affected = run(frame(a=["1", "100"]), "flag_outliers", "a")
    assert affected == 0  # ít dữ liệu: không kết luận
    for bad in [{"method": "median"}, {"threshold": 0}, {"threshold": "x"}]:
        with pytest.raises(RuleError):
            run(df, "flag_outliers", "tuoi", **bad)


# ---------------------------------------------------------------- cột


def test_rename_and_drop_column():
    df = frame(a=["1"], b=["2"])
    renamed, affected = run(df, "rename_column", "a", new_name="  x  ")
    assert list(renamed.columns) == ["x", "b"] and affected == 0
    with pytest.raises(RuleError, match="đã tồn tại"):
        run(df, "rename_column", "a", new_name="b")
    for bad in ("", None, "   "):
        with pytest.raises(RuleError, match="new_name"):
            run(df, "rename_column", "a", new_name=bad)
    with pytest.raises(RuleError):
        run(df, "rename_column", "a", new_name="x" * 300)
    dropped, _ = run(df, "drop_column", "a")
    assert list(dropped.columns) == ["b"]
    with pytest.raises(RuleError, match="cuối cùng"):
        run(dropped, "drop_column", "b")


# ---------------------------------------------------------------- engine


def test_missing_column_is_reported_with_step_number():
    df = frame(a=["x"])
    rule_set = RuleSet.model_validate(
        {
            "steps": [
                {"op": "trim_whitespace", "column": "a"},
                {"op": "trim_whitespace", "column": "khong_co"},
            ]
        }
    )
    with pytest.raises(RuleError, match="Bước 2.*khong_co"):
        apply_rules(df, rule_set)


def test_steps_run_in_order_and_later_steps_see_earlier_changes():
    df = frame(a=[" hcm "])
    rule_set = RuleSet.model_validate(
        {
            "steps": [
                {"op": "trim_whitespace", "column": "a"},
                {"op": "replace_values", "column": "a", "params": {"mapping": {"hcm": "HCM"}}},
                {"op": "rename_column", "column": "a", "params": {"new_name": "tinh"}},
                {"op": "change_case", "column": "tinh", "params": {"mode": "lower"}},
            ]
        }
    )
    result, steps = apply_rules(df, rule_set)
    assert list(result.columns) == ["tinh"] and result["tinh"][0] == "hcm"
    assert [s.affected_rows for s in steps] == [1, 1, 0, 1]


def test_empty_and_oversized_rule_sets_rejected():
    df = frame(a=["x"])
    with pytest.raises(RuleError, match="Không có bước"):
        apply_rules(df, RuleSet(steps=[]))
    big = RuleSet.model_validate(
        {"steps": [{"op": "trim_whitespace", "column": "a"}] * (MAX_STEPS + 1)}
    )
    with pytest.raises(RuleError, match="tối đa"):
        apply_rules(df, big)


def test_dry_run_does_not_touch_original():
    df = frame(a=[" x "])
    after, _ = dry_run(
        df, RuleSet.model_validate({"steps": [{"op": "trim_whitespace", "column": "a"}]})
    )
    assert after["a"][0] == "x" and df["a"][0] == " x "


def test_changed_row_labels_counts_deleted_changed_and_flagged():
    before = frame(a=["x", "y", "z", "w"])
    after = before.drop(index=[1]).copy()
    after.loc[2, "a"] = "Z"
    after["a_is_outlier"] = ["False", "False", "False"]
    assert changed_row_labels(before, after) == {1, 2}  # dòng 0 chỉ có cờ False
    after.loc[0, "a_is_outlier"] = "True"
    assert changed_row_labels(before, after) == {0, 1, 2}


def test_large_column_is_fast_enough():
    n = 200_000
    df = frame(a=[" Hà Nội ", "HCM", "Đà Nẵng", "  x"] * (n // 4))
    result, affected = run(df, "trim_whitespace", "a")
    assert affected == n // 2 and len(result) == n
