"""Rule Engine giả và bộ sinh gợi ý của mock: từng op, xem trước, hội tụ về dữ liệu sạch."""

import pandas as pd
import pytest

import mock_data
import mock_rules
import mock_suggest


def frame(**columns) -> pd.DataFrame:
    return pd.DataFrame({k: list(v) for k, v in columns.items()})


def step(op, column=None, **params):
    return {"op": op, "column": column, "params": params}


def run(df, *steps):
    result, per_step, affected = mock_rules.apply_steps(df, list(steps))
    return result, per_step, affected


# ---------------------------------------------------------------- từng op


def test_trim_and_case_and_replace():
    df = frame(a=[" An ", "Bình", ""])
    out, per, _ = run(df, step("trim_whitespace", "a"))
    assert list(out["a"]) == ["An", "Bình", ""] and per == [1]
    out, *_ = run(df, step("change_case", "a", mode="upper"))
    assert out["a"][1] == "BÌNH"
    out, per, _ = run(df, step("replace_values", "a", mapping={"Bình": "Bình An"}))
    assert out["a"][1] == "Bình An" and per == [1]


def test_standardize_date_mixed_formats_and_invalid_kept():
    df = frame(d=["15/04/1990", "1995-03-12", "31/02/2000", "N/A"])
    out, per, _ = run(df, step("standardize_date", "d", output_format="%Y-%m-%d"))
    assert list(out["d"]) == ["1990-04-15", "1995-03-12", "31/02/2000", "N/A"]
    assert per == [1]  # chỉ ô đã đổi; ô đã chuẩn, không parse được và null-token giữ nguyên


def test_standardize_phone_formats():
    df = frame(p=["0912 345 678", "+84 933 445 566", "090-555-1234", "0966", "84912345678"])
    out, *_ = run(df, step("standardize_phone", "p", region="VN", output_format="E164"))
    assert list(out["p"]) == [
        "+84912345678",
        "+84933445566",
        "+84905551234",
        "0966",
        "+84912345678",
    ]
    out, *_ = run(df, step("standardize_phone", "p", output_format="NATIONAL"))
    assert out["p"][1] == "0933445566"


def test_standardize_email_and_drop_invalid():
    df = frame(e=[" A@B.com ", "sai-cu-phap", ""])
    out, per, _ = run(df, step("standardize_email", "e", drop_invalid=False))
    assert list(out["e"]) == ["a@b.com", "sai-cu-phap", ""] and per == [1]
    out, per, _ = run(df, step("standardize_email", "e", drop_invalid=True))
    assert list(out["e"]) == ["a@b.com", "", ""] and per == [2]


@pytest.mark.parametrize(
    ("strategy", "extra", "expected"),
    [
        ("constant", {"value": "0"}, ["10", "0", "30", "0"]),
        ("mean", {}, ["10", "20", "30", "20"]),
        ("median", {}, ["10", "20", "30", "20"]),
        ("mode", {}, ["10", "10", "30", "10"]),
        ("ffill", {}, ["10", "10", "30", "30"]),
        ("bfill", {}, ["10", "30", "30", ""]),
    ],
)
def test_fill_missing_strategies(strategy, extra, expected):
    values = ["10", "N/A", "30", ""] if strategy != "mode" else ["10", "N/A", "30", "10"]
    if strategy == "mode":
        values = ["10", "N/A", "30", "10"]
        expected = ["10", "10", "30", "10"]
    df = frame(x=values)
    out, *_ = run(df, step("fill_missing", "x", strategy=strategy, **extra))
    assert list(out["x"]) == expected


def test_drop_duplicates_and_rows_where():
    df = frame(a=["x", "x", "y"], b=["1", "1", "2"])
    out, per, affected = run(df, step("drop_duplicates"))
    assert len(out) == 2 and per == [1] and affected == {1}
    out, per, _ = run(
        frame(n=["5", "-5", "N/A", "150"]), step("drop_rows_where", "n", operator="lt", value=0)
    )
    assert list(out["n"]) == ["5", "N/A", "150"] and per == [1]
    out, *_ = run(frame(n=["5", "N/A", ""]), step("drop_rows_where", "n", operator="is_null"))
    assert list(out["n"]) == ["5"]


def test_flag_outliers_adds_flag_column_without_deleting_rows():
    df = frame(age=["29", "34", "31", "30", "28", "32", "33", "150", "-5"])
    out, per, _ = run(df, step("flag_outliers", "age", method="iqr", threshold=1.5))
    assert len(out) == 9 and per == [2]
    assert out.loc[out["age"] == "150", "age_is_outlier"].item() == "True"
    assert out.loc[out["age"] == "29", "age_is_outlier"].item() == "False"


def test_rename_and_drop_column_and_conflicts():
    df = frame(a=["1"], b=["2"])
    out, *_ = run(df, step("rename_column", "a", new_name="ho_ten"))
    assert list(out.columns) == ["ho_ten", "b"]
    out, *_ = run(df, step("drop_column", "b"))
    assert list(out.columns) == ["a"]
    with pytest.raises(mock_rules.RuleError, match="đã tồn tại"):
        run(df, step("rename_column", "a", new_name="b"))


def test_cast_type():
    out, per, _ = run(frame(n=["1,5", "x", "7"]), step("cast_type", "n", target_type="int"))
    assert list(out["n"]) == ["1", "", "7"] and per == [2]


# ---------------------------------------------------------------- kiểm tra rule


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ([{"op": "exec_code", "column": "a"}], "không được hỗ trợ"),
        ([{"op": "trim_whitespace"}], "yêu cầu phải chỉ định column"),
        ("không phải danh sách", "phải là một danh sách"),
    ],
)
def test_validate_steps_rejects_invalid_rules(steps, message):
    with pytest.raises(mock_rules.RuleError, match=message):
        mock_rules.validate_steps(steps)


def test_unknown_column_is_reported():
    with pytest.raises(mock_rules.RuleError, match="không tồn tại"):
        run(frame(a=["1"]), step("trim_whitespace", "khong_co"))


def test_steps_run_in_order():
    df = frame(a=["x"])
    out, *_ = run(df, step("rename_column", "a", new_name="b"), step("trim_whitespace", "b"))
    assert list(out.columns) == ["b"]
    with pytest.raises(mock_rules.RuleError):  # sau khi đổi tên, cột cũ không còn
        run(df, step("rename_column", "a", new_name="b"), step("trim_whitespace", "a"))


# ---------------------------------------------------------------- xem trước


def test_preview_diffs_and_counts():
    df = frame(a=[" x", "y", " x"], b=["1", "2", "1"])
    result = mock_rules.compute_preview(df, [step("trim_whitespace", "a")], 50)
    assert [(d["row_index"], d["column"], d["before"], d["after"]) for d in result["diffs"]] == [
        (0, "a", " x", "x"),
        (2, "a", " x", "x"),
    ]
    assert result["affected_row_count"] == 2
    assert len(result["before_rows"]) == len(result["after_rows"]) == 3


def test_preview_respects_sample_size_and_drop_rows():
    df = frame(a=["x", "x", "y", "z"])
    result = mock_rules.compute_preview(df, [step("drop_duplicates")], 3)
    assert len(result["before_rows"]) == 3 and len(result["after_rows"]) == 2
    assert result["diffs"] == [] and result["affected_row_count"] == 1


# ---------------------------------------------------------------- bộ sinh gợi ý


def test_suggestions_for_sample_data():
    found = mock_suggest.generate(mock_data.sample_frame())
    ops = [(s["target_column"], s["proposed_rule"]["steps"][0]["op"]) for s in found]
    assert ops == [
        (None, "drop_duplicates"),
        ("email", "trim_whitespace"),
        ("email", "standardize_email"),
        ("so_dien_thoai", "standardize_phone"),
        ("ngay_sinh", "standardize_date"),
        ("tuoi", "flag_outliers"),
        ("tuoi", "fill_missing"),
        ("tinh_thanh", "replace_values"),
    ]
    assert {s["source"] for s in found} == {"rule_engine", "ai"}
    assert all(0 <= s["confidence"] <= 1 and s["explanation"] for s in found)
    mapping = next(s for s in found if s["target_column"] == "tinh_thanh")["proposed_rule"][
        "steps"
    ][0]
    assert mapping["params"]["mapping"]["HCM"] == "TP. Hồ Chí Minh"


def test_suggestions_converge_to_clean_data():
    df, rounds = mock_data.sample_frame(), 0
    while True:
        found = mock_suggest.generate(df)
        if not found:
            break
        df, *_ = mock_rules.apply_steps(df, [s["proposed_rule"]["steps"][0] for s in found])
        rounds += 1
        assert rounds <= 4, "gợi ý lặp vô hạn"
    assert rounds >= 2  # vòng 2 còn email sai cú pháp


def test_clean_frame_has_no_suggestions():
    assert mock_suggest.generate(frame(a=["x", "y"], b=["1", "2"])) == []


# ---------------------------------------------------------------- tô màu bảng xem trước


def _preview(df, *steps, sample_rows=50):
    result = mock_rules.compute_preview(df, list(steps), sample_rows)
    return result["before_rows"], result["after_rows"], result["diffs"]


def test_changed_cells_aligns_rows_after_deduplication():
    from components.diff_table import changed_cells

    df = frame(a=[" x", "y", "y", "z"], b=["1", "2", "2", "3"])
    before, after, diffs = _preview(df, step("drop_duplicates"), step("trim_whitespace", "a"))
    assert len(after) == 3  # một dòng "y" bị xóa
    assert changed_cells(before, after, diffs) == {(0, "a")}  # chỉ ô " x" -> "x"


def test_changed_cells_marks_new_columns_and_none_without_diffs():
    from components.diff_table import changed_cells

    df = frame(age=["29", "34", "31", "30", "28", "32", "33", "150"])
    before, after, diffs = _preview(df, step("flag_outliers", "age", method="iqr", threshold=1.5))
    cells = changed_cells(before, after, diffs)
    assert {(r, "age_is_outlier") for r in range(8)} <= cells
    assert changed_cells(before, after, None) is None


def test_changed_cells_returns_none_when_rows_cannot_be_matched():
    from components.diff_table import changed_cells

    before = [{"a": "x"}, {"a": "y"}]
    assert changed_cells(before, [{"a": "KHAC"}], []) is None


def test_visible_marks_whitespace_and_blanks():
    from components.diff_table import _visible

    assert _visible("a@b.com ") == '"a@b.com "'
    assert _visible("ok") == "ok"
    assert _visible("") == "(trống)" and _visible(None) == "(trống)"
