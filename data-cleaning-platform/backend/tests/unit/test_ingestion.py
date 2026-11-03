"""Đọc file đầu vào: encoding, delimiter, dòng tiêu đề thật, CSV/Excel lỗi."""

import io
import unicodedata

import pandas as pd
import pytest

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.services.ingestion.delimiter import detect_delimiter
from app.services.ingestion.encoding import detect_encoding
from app.services.ingestion.header_detect import detect_header_row
from app.services.ingestion.reader import read_dataset_file
from tests.conftest import FIXTURES_DIR

VN_CSV = "ho_ten,tinh\nNguyễn Văn An,Hồ Chí Minh\nTrần Thị Bình,Đà Nẵng\n"


# ---------------------------------------------------------------- encoding


def test_utf8_and_bom_detected():
    assert detect_encoding(VN_CSV.encode("utf-8")) == "utf-8"
    assert detect_encoding(b"\xef\xbb\xbf" + VN_CSV.encode("utf-8")) == "utf-8-sig"


def _to_cp1258(text: str) -> bytes:
    """Mã hóa như Windows tiếng Việt: giữ ký tự dựng sẵn nếu cp1258 có, còn lại tách dấu thanh."""
    out = bytearray()
    for char in text:
        try:
            out += char.encode("cp1258")
        except UnicodeEncodeError:
            decomposed = unicodedata.normalize("NFD", char)
            tone = decomposed[-1] if decomposed[-1] in "̣̀́̃̉" else ""
            base = unicodedata.normalize("NFC", decomposed[: len(decomposed) - len(tone)])
            out += base.encode("cp1258") + tone.encode("cp1258")
    return bytes(out)


def test_cp1258_file_is_read_with_correct_vietnamese():
    text = (
        "ho_ten,tinh,ghi_chu\n"
        + "Nguyễn Thị Hương,Thành phố Hồ Chí Minh,Khách hàng thân thiết\n" * 20
    )
    # cp1258 lưu chữ có dấu dạng tổ hợp (NFD): đúng như file Windows tiếng Việt cũ.
    result = read_dataset_file(_to_cp1258(text), "khach.csv")
    assert result.encoding is not None and result.encoding.lower() != "utf-8"
    assert result.dataframe["ho_ten"][0] == "Nguyễn Thị Hương"


def test_empty_bytes_fall_back_to_utf8():
    assert detect_encoding(b"abc") == "utf-8"


# ---------------------------------------------------------------- delimiter


@pytest.mark.parametrize("sep", [",", ";", "\t", "|"])
def test_delimiter_detected(sep):
    sample = "\n".join(sep.join(row) for row in [["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]])
    assert detect_delimiter(sample) == sep


def test_delimiter_ignores_separators_inside_quotes():
    sample = 'a,b,c\n"x, y; z",2,3\n"p, q",5,6\n'
    assert detect_delimiter(sample) == ","


def test_delimiter_single_column_falls_back_to_comma():
    assert detect_delimiter("chi_mot_cot\nA\nB\n") == ","
    assert detect_delimiter("") == ","


# ---------------------------------------------------------------- header


def test_header_row_zero_for_clean_file():
    df = pd.DataFrame([["a", "b", "c"], ["1", "2", "3"], ["4", "5", "6"]])
    assert detect_header_row(df) == 0


def test_header_row_skips_title_and_blank_rows():
    df = pd.DataFrame(
        [
            ["BÁO CÁO NHÂN SỰ", "", "", ""],
            ["", "", "", ""],
            ["Xuất ngày 01/01/2026", "", "", ""],
            ["ho_ten", "email", "sdt", "tuoi"],
            ["An", "a@x.vn", "0901", "29"],
        ]
    )
    assert detect_header_row(df) == 3


def test_header_row_numeric_first_row_is_still_row_zero():
    df = pd.DataFrame([["1", "2", "3"], ["4", "5", "6"]])
    assert detect_header_row(df) == 0


# ---------------------------------------------------------------- CSV


def test_values_are_kept_as_text_exactly():
    content = b"ten,sdt,tuoi\n  An ,0901234567,29\nBinh,,N/A\n"
    frame = read_dataset_file(content, "a.csv").dataframe
    assert frame["sdt"][0] == "0901234567"  # số 0 đầu không mất
    assert frame["ten"][0] == "  An "  # khoảng trắng không bị tự cắt
    assert frame["sdt"][1] == "" and frame["tuoi"][1] == "N/A"
    assert list(frame.dtypes.astype(str).unique()) == ["object"] or frame.dtypes.nunique() == 1


def test_vietnamese_headers_are_preserved():
    path = FIXTURES_DIR.parent.parent.parent / "sample_data" / "khach_hang_tieu_de_khac.csv"
    result = read_dataset_file(path.read_bytes(), path.name)
    assert list(result.dataframe.columns)[:3] == ["Họ và tên", "Email liên hệ", "Số ĐT"]
    assert len(result.dataframe) > 5


def test_csv_with_junk_lines_before_header():
    content = "BÁO CÁO\n\nho_ten,tuoi,tinh\nAn,29,HN\nBình,34,HCM\n".encode()
    frame = read_dataset_file(content, "r.csv").dataframe
    assert list(frame.columns) == ["ho_ten", "tuoi", "tinh"] and len(frame) == 2


def test_duplicate_and_empty_headers_are_made_unique():
    content = b"a,a,,b\n1,2,3,4\n5,6,7,8\n"
    assert list(read_dataset_file(content, "a.csv").dataframe.columns) == [
        "a",
        "a_2",
        "cot_3",
        "b",
    ]


def test_trailing_empty_column_and_blank_rows_dropped():
    content = b"a,b,\n1,2,\n\n3,4,\n"
    frame = read_dataset_file(content, "a.csv").dataframe
    assert list(frame.columns) == ["a", "b"] and len(frame) == 2


def test_quoted_fields_with_newlines_and_commas():
    content = 'a,b\n"dòng 1\ndòng 2","x, y"\n'.encode()
    frame = read_dataset_file(content, "a.csv").dataframe
    assert frame["a"][0] == "dòng 1\ndòng 2" and frame["b"][0] == "x, y"


def test_semicolon_csv():
    frame = read_dataset_file(b"a;b\n1;2\n3;4\n", "a.csv").dataframe
    assert list(frame.columns) == ["a", "b"] and len(frame) == 2


def test_header_only_and_empty_files_rejected():
    for content in (b"a,b,c\n", b"\n\n", b"   "):
        with pytest.raises(ValidationAppError):
            read_dataset_file(content, "a.csv")


def test_ragged_rows_rejected_with_clear_message():
    content = b"a,b\n1,2\n3,4,5,6,7\n" + b"x,y\n" * 300 + b"1,2,3\n"
    # dòng dài hơn mọi dòng trong mẫu đầu file -> lỗi cấu trúc (không âm thầm mất dữ liệu)
    big = b"a,b\n" + b"1,2\n" * 500 + b"1,2,3,4\n"
    with pytest.raises(ValidationAppError, match="CSV"):
        read_dataset_file(big, "a.csv")
    assert content  # nội dung thứ nhất vẫn đọc được vì độ rộng tính theo mẫu đầu file
    assert len(read_dataset_file(content, "a.csv").dataframe.columns) >= 2


def test_row_and_column_limits(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_ROWS", 3)
    with pytest.raises(ValidationAppError, match="dòng"):
        read_dataset_file(b"a\n1\n2\n3\n4\n", "a.csv")
    monkeypatch.setattr(settings, "MAX_UPLOAD_COLUMNS", 2)
    with pytest.raises(ValidationAppError, match="cột"):
        read_dataset_file(b"a,b,c\n1,2,3\n", "a.csv")


# ---------------------------------------------------------------- loại file / chữ ký


def test_unsupported_extension_rejected():
    for name in ("virus.exe", "a.txt", "noext", "a.csv.exe"):
        with pytest.raises(ValidationAppError, match="Định dạng"):
            read_dataset_file(b"a,b\n1,2\n", name)


def test_binary_and_mismatched_content_rejected():
    with pytest.raises(ValidationAppError):
        read_dataset_file(b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 100, "a.csv")
    with pytest.raises(ValidationAppError):
        read_dataset_file(b"a,b\n1,2\n", "a.xlsx")  # văn bản đội lốt Excel
    with pytest.raises(ValidationAppError):
        read_dataset_file(b"a,b\n1,2\n", "a.xls")
    xlsx = (FIXTURES_DIR / "dirty_sample.xlsx").read_bytes()
    with pytest.raises(ValidationAppError, match="Excel"):
        read_dataset_file(xlsx, "a.csv")  # Excel đội lốt CSV


def test_corrupted_xlsx_rejected():
    with pytest.raises(ValidationAppError):
        read_dataset_file(b"PK\x03\x04" + b"rac" * 50, "a.xlsx")


# ---------------------------------------------------------------- Excel


def _xlsx(sheets: dict[str, list[list]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, header=False, index=False)
    return buffer.getvalue()


def test_excel_multiple_sheets_and_selection():
    content = _xlsx(
        {
            "Khach": [["ten", "tuoi"], ["An", 29], ["Bình", 34]],
            "NhanSu": [["ma", "phong"], ["E1", "IT"]],
        }
    )
    first = read_dataset_file(content, "a.xlsx")
    assert first.sheet_names == ["Khach", "NhanSu"] and first.used_sheet == "Khach"
    assert first.dataframe["tuoi"][0] == "29"  # số nguyên không thành "29.0"
    second = read_dataset_file(content, "a.xlsx", sheet_name="NhanSu")
    assert list(second.dataframe.columns) == ["ma", "phong"]
    with pytest.raises(ValidationAppError, match="Sheet"):
        read_dataset_file(content, "a.xlsx", sheet_name="KhongCo")


def test_excel_dates_lose_midnight_time():
    content = _xlsx({"S": [["ten", "ngay"], ["An", pd.Timestamp("1995-03-12")]]})
    assert read_dataset_file(content, "a.xlsx").dataframe["ngay"][0] == "1995-03-12"


def test_excel_empty_sheet_rejected():
    content = _xlsx({"Trong": [[None, None]], "Co": [["a"], ["1"]]})
    with pytest.raises(ValidationAppError):
        read_dataset_file(content, "a.xlsx", sheet_name="Trong")


def test_real_fixture_xlsx_reads():
    frame = read_dataset_file((FIXTURES_DIR / "dirty_sample.xlsx").read_bytes(), "x.xlsx").dataframe
    assert len(frame) > 0 and len(frame.columns) >= 3
