"""Mapping tên cột tầng 1: chuẩn hóa, từ điển đồng nghĩa, fuzzy matching."""

import pytest

from app.services.mapping.matcher import match_columns
from app.services.mapping.normalizer import normalize_column_name
from app.services.mapping.synonyms import find_canonical_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Tỉnh/Thành phố", "tinh_thanh_pho"),
        ("Số ĐT", "so_dt"),
        (" E-mail ", "e_mail"),
        ("Họ và tên", "ho_va_ten"),
        ("ho_ten", "ho_ten"),
        ("__A--B__", "a_b"),
        ("", ""),
        ("???", ""),
    ],
)
def test_normalize_column_name(raw, expected):
    assert normalize_column_name(raw) == expected


def test_synonym_lookup():
    assert find_canonical_name("sdt") == "so_dien_thoai"
    assert find_canonical_name("so_dien_thoai") == "so_dien_thoai"
    assert find_canonical_name("tinh_thanh_pho") == "tinh_thanh"
    assert find_canonical_name("ho_va_ten") == "ho_ten"
    assert find_canonical_name("khong_co_trong_tu_dien") is None


TARGET = ["ho_ten", "email", "so_dien_thoai", "ngay_sinh", "tuoi", "tinh_thanh"]


def test_demo_file_headers_map_to_standard_schema():
    source = [
        "Họ và tên",
        "Email liên hệ",
        "Số ĐT",
        "Ngày sinh",
        "Tuổi",
        "Tỉnh/Thành phố",
        "Ghi chú",
    ]
    assert match_columns(source, TARGET) == {
        "Họ và tên": "ho_ten",
        "Email liên hệ": "email",  # gần giống (fuzzy) hoặc đồng nghĩa
        "Số ĐT": "so_dien_thoai",
        "Ngày sinh": "ngay_sinh",
        "Tuổi": "tuoi",
        "Tỉnh/Thành phố": "tinh_thanh",
        "Ghi chú": None,
    }


def test_exact_names_and_result_keeps_source_order():
    source = ["tuoi", "email", "ho_ten"]
    result = match_columns(source, TARGET)
    assert list(result) == source and result == {
        "tuoi": "tuoi",
        "email": "email",
        "ho_ten": "ho_ten",
    }


def test_synonyms_between_source_and_target_names():
    # cả hai đều là biến thể của so_dien_thoai
    assert match_columns(["SDT"], ["phone_number"]) == {"SDT": "phone_number"}
    assert match_columns(["Phone"], ["Số điện thoại"]) == {"Phone": "Số điện thoại"}


def test_typo_matches_by_fuzzy_but_unrelated_does_not():
    assert match_columns(["ngay_sihn"], TARGET) == {"ngay_sihn": "ngay_sinh"}
    assert match_columns(["luong_thang", "xyz"], TARGET) == {"luong_thang": None, "xyz": None}


def test_each_target_used_once_best_source_wins():
    result = match_columns(["email", "email_lien_he"], ["email"])
    assert result == {"email": "email", "email_lien_he": None}
    result = match_columns(["email_lien_he", "email"], ["email"])
    assert result == {"email_lien_he": None, "email": "email"}


def test_empty_inputs_and_blank_names():
    assert match_columns([], TARGET) == {}
    assert match_columns(["a", "b"], []) == {"a": None, "b": None}
    assert match_columns(["???"], ["???"]) == {"???": None}  # tên rỗng sau chuẩn hóa: không đoán
    assert match_columns(["email"], ["email", "email"]) == {"email": "email"}
