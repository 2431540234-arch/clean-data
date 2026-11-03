"""Profiling (kiểu, thống kê cột) và 8 detector lỗi dữ liệu."""

import pandas as pd
import pytest

from app.services.detectors import run_all_detectors
from app.services.detectors.dates import DatesDetector
from app.services.detectors.duplicates import DuplicatesDetector
from app.services.detectors.emails import EmailsDetector
from app.services.detectors.inconsistency import InconsistencyDetector
from app.services.detectors.missing import MissingDetector
from app.services.detectors.outliers import OutliersDetector
from app.services.detectors.phones import PhonesDetector
from app.services.detectors.whitespace_case import WhitespaceCaseDetector
from app.services.profiling import values as v
from app.services.profiling.profiler import profile_dataframe
from app.services.profiling.type_inference import infer_column_type


def S(*items) -> pd.Series:
    return pd.Series(list(items), dtype=str)


def frame(**columns) -> pd.DataFrame:
    return pd.DataFrame({k: list(vals) for k, vals in columns.items()}, dtype=str)


def only(issues, kind):
    found = [i for i in issues if i.extra.get("kind") == kind]
    assert len(found) == 1, [i.extra.get("kind") for i in issues]
    return found[0]


# ---------------------------------------------------------------- giá trị cơ bản


@pytest.mark.parametrize("value", ["", "  ", "N/A", "n/a", "-", "null", "Không có", "?", None])
def test_null_tokens(value):
    assert v.is_null(value)


def test_real_values_are_not_null():
    for value in ["0", "-5", "abc", "Hà Nội"]:
        assert not v.is_null(value)


def test_date_parsing_rejects_impossible_dates_and_detects_formats():
    assert v.date_format_of("15/04/1990") == "dd/MM/yyyy"
    assert v.date_format_of("1995-03-12") == "yyyy-MM-dd"
    assert v.date_format_of("12.03.1995") == "dd.MM.yyyy"
    assert v.date_format_of("03/25/1990") == "MM/dd/yyyy"  # tháng 25 không có -> kiểu Mỹ
    assert v.date_format_of("31/02/2024") is None
    assert v.date_format_of("abc") is None
    assert v.date_format_of("2024-13-01") is None


def test_phone_validation_and_shapes():
    assert v.is_valid_phone("0901234567") and v.is_valid_phone("+84 933 445 566")
    assert v.is_valid_phone("090-555-1234")
    assert not v.is_valid_phone("12345") and not v.is_valid_phone("0000000000")
    assert v.phone_shape("0901234567") == "chỉ gồm chữ số"
    assert v.phone_shape("0912 345 678") == "có khoảng trắng"
    assert v.phone_shape("+84933445566") == "quốc tế (+84)"


# ---------------------------------------------------------------- suy luận kiểu


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        (["a@x.vn", "b@y.com", "c@z.org"], "email"),
        (["0901234567", "0912 345 678", "+84933445566"], "phone"),
        (["15/04/1990", "1995-03-12", "01/01/2000"], "date"),
        (["1", "22", "-5", "150"], "integer"),
        (["1.5", "2", "3,25"], "float"),
        (["có", "không", "có"], "boolean"),
        (["An", "Bình", "Cường"], "text"),
        ([], "text"),
        (["", "N/A", "-"], "text"),
    ],
)
def test_infer_type(values, expected):
    assert infer_column_type(S(*values)) == expected


def test_infer_type_tolerates_a_few_dirty_values():
    ages = ["29"] * 18 + ["N/A", "abc"]  # 18/19 giá trị khác rỗng là số
    assert infer_column_type(S(*ages)) == "integer"
    mostly_bad = ["29", "abc", "xyz", "pqr"]
    assert infer_column_type(S(*mostly_bad)) == "text"


def test_numeric_id_with_leading_zero_stays_text_free():
    assert infer_column_type(S("001", "002", "003")) == "integer"


# ---------------------------------------------------------------- profiler


def test_profile_dataframe_statistics():
    df = frame(
        tuoi=["29", "34", "", "N/A", "40"],
        ngay=["15/04/1990", "1995-03-12", "", "01/01/2000", "02/02/2002"],
        ten=["An", "Bình", "An", "", "Cường"],
    )
    by_name = {p.column_name: p for p in profile_dataframe(df)}
    age = by_name["tuoi"]
    assert (age.inferred_type, age.null_count, age.unique_count) == ("integer", 2, 3)
    assert age.null_ratio == pytest.approx(0.4) and age.unique_ratio == pytest.approx(0.6)
    assert (age.min_value, age.max_value, age.mean_value) == ("29", "40", 34.33)
    date = by_name["ngay"]
    assert date.inferred_type == "date"
    assert date.detected_format.startswith("Nhiều định dạng")
    assert (date.min_value, date.max_value) == ("1990-04-15", "2002-02-02")
    name = by_name["ten"]
    assert name.sample_values == ["An", "Bình", "Cường"] and name.column_index == 2


def test_profile_empty_dataframe_and_all_null_column():
    assert profile_dataframe(pd.DataFrame({"a": []}, dtype=str))[0].null_ratio == 0.0
    profile = profile_dataframe(frame(a=["", "", "N/A"]))[0]
    assert profile.null_count == 3 and profile.unique_count == 0 and profile.sample_values == []


# ---------------------------------------------------------------- detector: thiếu


def test_missing_detector_severity_and_tokens():
    df = frame(a=["x", "", "N/A", "-"], b=["1", "2", "3", "4"], c=["", "", "", "x"])
    issues = {i.column: i for i in MissingDetector().detect(df)}
    assert set(issues) == {"a", "c"}
    assert issues["a"].severity == "high" and issues["a"].affected_row_indices == [1, 2, 3]
    assert issues["c"].extra["tokens"]["(ô trống)"] == 3


# ---------------------------------------------------------------- detector: trùng


def test_exact_duplicates_only_later_copies_are_affected():
    df = frame(a=["x", "y", "x", "x"], b=["1", "2", "1", "1"])
    (issue,) = DuplicatesDetector().detect(df)
    assert issue.extra["kind"] == "exact_duplicate_rows" and issue.affected_row_indices == [2, 3]


def test_near_duplicates_ignore_case_accent_and_spaces():
    df = frame(
        id=["1", "2", "3", "4", "5"],
        ten=["Nguyễn Văn An", "nguyen van an ", "Trần Thị Bình", "Lê Văn Cường", "Phạm Thị Dung"],
        email=["an@gmail.com", "AN@gmail.com", "b@x.vn", "c@x.vn", "d@x.vn"],
    )
    issues = DuplicatesDetector().detect(df)
    near = only(issues, "near_duplicate_rows")
    assert near.affected_row_indices == [1]


def test_no_duplicates_and_tiny_frames():
    assert DuplicatesDetector().detect(frame(a=["x", "y"])) == []
    assert DuplicatesDetector().detect(frame(a=["x"])) == []
    assert DuplicatesDetector().detect(pd.DataFrame({"a": []}, dtype=str)) == []


# ---------------------------------------------------------------- detector: số


def test_outliers_and_type_mismatch():
    ages = ["29", "34", "37", "32", "26", "40", "31", "33", "150", "-5", "abc", "30", "28"]
    issues = OutliersDetector().detect(frame(tuoi=ages))
    outlier = only(issues, "iqr_outlier")
    assert outlier.severity == "high"
    assert sorted(outlier.affected_row_indices) == [8, 9]
    mismatch = only(issues, "non_numeric_in_numeric")
    assert mismatch.issue_type == "type_mismatch" and mismatch.affected_row_indices == [10]


def test_outliers_skip_small_or_constant_columns():
    assert OutliersDetector().detect(frame(a=["1", "2", "3", "999"])) == []  # < 8 giá trị
    assert OutliersDetector().detect(frame(a=["5"] * 8 + ["6"])) == []  # IQR = 0


# ---------------------------------------------------------------- detector: ngày, SĐT, email


def test_dates_mixed_formats_and_invalid():
    df = frame(d=["15/04/1990", "16/04/1990", "17/04/1990", "1995-03-12", "31/02/1990", "N/A"])
    issues = DatesDetector().detect(df)
    mixed = only(issues, "mixed_date_format")
    assert mixed.affected_row_indices == [3] and mixed.extra["dominant"] == "dd/MM/yyyy"
    invalid = only(issues, "invalid_date")
    assert invalid.issue_type == "invalid_format" and invalid.affected_row_indices == [4]


def test_dates_consistent_column_has_no_issue():
    assert DatesDetector().detect(frame(d=["15/04/1990", "16/04/1990"])) == []


def test_phones_invalid_and_mixed_shape():
    df = frame(p=["0901234567", "0912345678", "0933 445 566", "+84944556677", "12345", "N/A"])
    issues = PhonesDetector().detect(df, {"p": "phone"})
    assert only(issues, "invalid_phone").affected_row_indices == [4]
    mixed = only(issues, "mixed_phone_format")
    assert sorted(mixed.affected_row_indices) == [2, 3]


def test_emails_invalid_and_untidy():
    df = frame(e=["a@x.vn", " B@X.VN ", "c@y.com", "d@z.org", "bad@invalid", ""])
    issues = EmailsDetector().detect(df, {"e": "email"})
    assert only(issues, "invalid_email").affected_row_indices == [4]
    assert only(issues, "email_case_whitespace").affected_row_indices == [1]


# ---------------------------------------------------------------- detector: văn bản


def test_whitespace_detector_flags_edges_and_double_spaces_not_newlines():
    df = frame(ten=["An", " Bình", "Cường  Nam", "Dung", "Em\nThêm"])
    (issue,) = [
        i for i in WhitespaceCaseDetector().detect(df) if i.extra["kind"] == "extra_whitespace"
    ]
    assert issue.affected_row_indices == [1, 2]


def test_mixed_case_ignores_short_abbreviations():
    names = ["Nguyễn An", "Trần Bình", "Lê Cường", "BÙI THỊ HOA", "VŨ VĂN ĐẠT", "phạm dung"] * 2
    issue = only(WhitespaceCaseDetector().detect(frame(ten=names)), "mixed_case")
    assert issue.extra["dominant_style"] == "title" and len(issue.affected_row_indices) == 6
    provinces = ["Hà Nội"] * 5 + ["HCM", "HN", "VIP"]
    assert not [
        i
        for i in WhitespaceCaseDetector().detect(frame(t=provinces))
        if i.extra["kind"] == "mixed_case"
    ]


def test_inconsistency_province_variants_map_to_canonical():
    values = (
        ["TP. Hồ Chí Minh"] * 4
        + ["HCM", "TP.HCM", "Hồ Chí Minh"]
        + ["Hà Nội"] * 3
        + ["Ha Noi", "HN"]
    )
    issue = only(InconsistencyDetector().detect(frame(tinh=values)), "value_variants")
    mapping = issue.extra["mapping"]
    assert mapping["HCM"] == "TP. Hồ Chí Minh" and mapping["Ha Noi"] == "Hà Nội"
    assert "TP. Hồ Chí Minh" not in mapping and len(issue.affected_row_indices) == 5


def test_inconsistency_generic_groups_by_accent_case_punctuation():
    values = ["Nam"] * 5 + ["nam", "NAM"] + ["Nữ"] * 5 + ["nu"]
    issue = only(InconsistencyDetector().detect(frame(gt=values)), "value_variants")
    assert issue.extra["mapping"] == {"nam": "Nam", "NAM": "Nam", "nu": "Nữ"}
    assert not issue.extra["province"]


def test_inconsistency_skips_unique_text_and_numbers():
    names = [f"Người số {i}" for i in range(20)]
    assert InconsistencyDetector().detect(frame(ten=names)) == []
    assert InconsistencyDetector().detect(frame(n=["1", "2", "1", "2"])) == []


# ---------------------------------------------------------------- run_all


def test_run_all_detectors_orders_by_severity_and_survives_detector_errors(monkeypatch):
    df = frame(tuoi=["29", "34", "37", "32", "26", "40", "31", "33", "150", "30"], e=["a"] * 10)
    issues = run_all_detectors(df)
    severities = [i.severity for i in issues]
    assert severities == sorted(severities, key={"high": 0, "medium": 1, "low": 2}.get)

    def boom(self, *args, **kwargs):
        raise RuntimeError("hỏng")

    monkeypatch.setattr(MissingDetector, "detect", boom)
    assert run_all_detectors(df)  # các detector còn lại vẫn chạy
