"""Điểm chất lượng (công thức tính tay) và xuất file (CSV/Excel, chống chèn công thức)."""

import io

import pandas as pd
import pytest
from openpyxl import load_workbook

from app.services.export import export_to_csv_bytes, export_to_excel_bytes, neutralize_formulas
from app.services.quality import QUALITY_WEIGHTS, compute_quality_score


def frame(**columns) -> pd.DataFrame:
    return pd.DataFrame({k: list(v) for k, v in columns.items()}, dtype=str)


def test_weights_sum_to_one():
    assert sum(QUALITY_WEIGHTS.values()) == pytest.approx(1.0)


def test_perfect_data_scores_100():
    metrics = compute_quality_score(frame(a=["x", "y", "z"], b=["1", "2", "3"]))
    assert metrics.overall_score == 100.0
    assert (metrics.completeness, metrics.uniqueness, metrics.validity, metrics.consistency) == (
        1.0,
        1.0,
        1.0,
        1.0,
    )


def test_missing_cells_lower_completeness_only():
    df = frame(a=["a", "b", "c", "d", "e"], b=["1", "2", "3", "4", ""])
    metrics = compute_quality_score(df)
    assert metrics.completeness == 0.9  # 1 ô thiếu / 10 ô
    assert metrics.overall_score == 97.0  # 100 * (0.3*0.9 + 0.2 + 0.3 + 0.2)
    assert metrics.issue_summary["missing_cells"] == 1


def test_duplicate_rows_lower_uniqueness():
    metrics = compute_quality_score(frame(a=["x", "x", "y", "z"], b=["1", "1", "2", "3"]))
    assert metrics.uniqueness == 0.75
    assert metrics.overall_score == 95.0
    assert metrics.issue_summary["duplicate_rows"] == 1


def test_invalid_values_lower_validity():
    emails = ["a@x.vn", "b@x.vn", "c@x.vn", "d@x.vn", "bad@x"]
    metrics = compute_quality_score(frame(e=emails))
    assert metrics.validity == 0.8 and metrics.overall_score == 94.0
    assert metrics.issue_summary["invalid_values"] == 1


def test_inconsistent_values_lower_consistency_and_cells_counted_once():
    values = ["Nam"] * 8 + ["nam", "NAM"]
    metrics = compute_quality_score(frame(gt=values))
    assert metrics.consistency == 0.8  # 2 ô khác cách viết / 10 ô
    # ô vừa thừa khoảng trắng vừa là biến thể vẫn chỉ trừ một lần
    messy = compute_quality_score(frame(gt=["Nam"] * 8 + [" nam", "NAM"]))
    assert messy.issue_summary["inconsistent_values"] <= 2


def test_outliers_count_against_validity_and_scores_stay_in_range():
    ages = ["29", "34", "37", "32", "26", "40", "31", "33", "150", "-5"]
    metrics = compute_quality_score(frame(tuoi=ages))
    assert metrics.validity == 0.8 and 0 <= metrics.overall_score <= 100


def test_empty_and_all_missing_frames_do_not_crash():
    assert compute_quality_score(pd.DataFrame({"a": []}, dtype=str)).overall_score == 100.0
    worst = compute_quality_score(frame(a=["", "N/A"], b=["-", ""]))
    assert worst.completeness == 0.0 and 0 <= worst.overall_score <= 100


def test_precomputed_issues_and_types_are_respected():
    df = frame(a=["x", "y"])
    metrics = compute_quality_score(df, issues=[], column_types={"a": "text"})
    assert metrics.overall_score == 100.0


# ---------------------------------------------------------------- xuất file


def test_csv_has_bom_and_keeps_vietnamese():
    content = export_to_csv_bytes(frame(ten=["Nguyễn Văn An"], tinh=["Hà Nội"]))
    assert content.startswith(b"\xef\xbb\xbf")
    assert "Nguyễn Văn An,Hà Nội" in content.decode("utf-8-sig")


def test_csv_neutralizes_formulas_but_keeps_numbers():
    df = frame(c=["=SUM(A1:A9)", "+84901234567", "-5", "@cmd", "bình thường", "-abc", "\t=1", ""])
    safe = list(neutralize_formulas(df)["c"])
    assert safe == [
        "'=SUM(A1:A9)",
        "+84901234567",
        "-5",
        "'@cmd",
        "bình thường",
        "'-abc",
        "'\t=1",
        "",
    ]
    csv_text = export_to_csv_bytes(df).decode("utf-8-sig")
    assert "'=SUM(A1:A9)" in csv_text and ",=SUM" not in csv_text


def test_csv_neutralizes_formula_like_column_names_and_never_mutates_input():
    df = frame(**{"=evil": ["1"]})
    assert export_to_csv_bytes(df).decode("utf-8-sig").startswith("'=evil")
    assert list(df.columns) == ["=evil"]


def test_excel_has_requested_sheets_and_formulas_stay_text():
    sheets = {
        "Dữ liệu": frame(ten=["=1+1", "@a", "An"]),
        "Báo cáo": pd.DataFrame({"Chỉ tiêu": ["x"], "Giá trị": [1]}),
    }
    workbook = load_workbook(io.BytesIO(export_to_excel_bytes(sheets)))
    assert workbook.sheetnames == ["Dữ liệu", "Báo cáo"]
    cell = workbook["Dữ liệu"]["A2"]
    assert cell.value == "=1+1" and cell.data_type == "s"


def test_excel_truncates_long_sheet_names():
    workbook = load_workbook(io.BytesIO(export_to_excel_bytes({"x" * 50: frame(a=["1"])})))
    assert len(workbook.sheetnames[0]) == 31
