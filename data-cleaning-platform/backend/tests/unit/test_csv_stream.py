"""Đọc CSV theo luồng phải cho kết quả giống hệt đọc cả file (read_dataset_file)."""

from pathlib import Path

import pandas as pd
import pytest

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.services.ingestion.csv_stream import stream_csv_to_parquet
from app.services.ingestion.reader import read_dataset_file
from tests.conftest import FIXTURES_DIR

SAMPLE_DIR = FIXTURES_DIR.parent.parent.parent / "sample_data"


def _both(tmp_path: Path, content: bytes, chunk_rows: int):
    source = tmp_path / "in.csv"
    source.write_bytes(content)
    expected = read_dataset_file(content, "in.csv")
    streamed = stream_csv_to_parquet(source, tmp_path / "out.parquet", chunk_rows=chunk_rows)
    return expected, streamed, pd.read_parquet(streamed.parquet_path)


def _assert_same(expected, streamed, frame):
    assert list(frame.columns) == list(expected.dataframe.columns) == streamed.columns
    assert streamed.row_count == len(frame) == len(expected.dataframe)
    assert streamed.encoding == expected.encoding
    assert frame.astype(str).equals(expected.dataframe.astype(str).reset_index(drop=True))
    assert streamed.preview.astype(str).equals(frame.head(20).astype(str).reset_index(drop=True))


@pytest.mark.parametrize("chunk_rows", [1, 3, 7, 1000])
@pytest.mark.parametrize(
    "path",
    [
        FIXTURES_DIR / "dirty_sample.csv",
        FIXTURES_DIR / "cp1258_sample.csv",
        SAMPLE_DIR / "khach_hang_tieu_de_khac.csv",
        SAMPLE_DIR / "khach_hang_ban.csv",
    ],
    ids=lambda p: p.name,
)
def test_streaming_matches_in_memory_on_real_samples(tmp_path, path, chunk_rows):
    _assert_same(*_both(tmp_path, path.read_bytes(), chunk_rows))


@pytest.mark.parametrize("chunk_rows", [1, 2, 5, 100])
@pytest.mark.parametrize(
    "text",
    [
        # dòng rác trước tiêu đề, dòng trống rải rác
        "BÁO CÁO\n\nTháng 10\nid,ten,email\n1,An,a@x.vn\n\n2,Bình,b@x.vn\n3,Chi,c@x.vn\n"
        "4,Dũng,d@x.vn\n5,Em,e@x.vn\n6,Giang,g@x.vn\n7,Hà,h@x.vn\n8,Khánh,k@x.vn\n9,Lan,l@x.vn\n",
        # cột thừa cuối dòng không tên, không dữ liệu
        "a,b,\n1,2,\n3,4,\n",
        # cột không tên nhưng có dữ liệu ở giữa file
        "a,b,\n1,2,\n3,4,x\n5,6,\n",
        # tiêu đề trùng và trống
        "ten,ten,,ten\n1,2,3,4\n5,6,7,8\n",
        # dấu chấm phẩy, trường có dấu nháy và xuống dòng
        'id;ghi_chu\n1;"dòng 1\ndòng 2"\n2;"có ; trong ô"\n3;bình thường\n',
        # BOM UTF-8
        "﻿id,ten\n1,An\n2,Bình\n",
        # ô toàn khoảng trắng và giá trị cần giữ nguyên
        'id,ten\n1,  An  \n2,   \n3,""\n',
    ],
)
def test_streaming_matches_in_memory_on_edge_cases(tmp_path, text, chunk_rows):
    _assert_same(*_both(tmp_path, text.encode("utf-8"), chunk_rows))


def test_streaming_matches_on_many_rows_across_chunks(tmp_path):
    lines = ["id,ten,so_dien_thoai"] + [f"{i},Tên {i},09{i:08d}" for i in range(2500)]
    expected, streamed, frame = _both(tmp_path, "\n".join(lines).encode("utf-8"), chunk_rows=400)
    _assert_same(expected, streamed, frame)
    assert streamed.row_count == 2500


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "không có dữ liệu"),
        (b"\n\n  \n", "không có dữ liệu"),
        (b"id,ten\n", "chỉ có dòng tiêu đề"),
        (b"PK\x03\x04abc", "Excel"),
        (b"a,b\x00\x01\n1,2\n", "không phải văn bản"),
    ],
)
def test_streaming_rejects_the_same_bad_files_as_in_memory(tmp_path, content, message):
    source = tmp_path / "in.csv"
    source.write_bytes(content)
    with pytest.raises(ValidationAppError) as expected:
        read_dataset_file(content, "in.csv")
    with pytest.raises(ValidationAppError) as got:
        stream_csv_to_parquet(source, tmp_path / "out.parquet")
    assert message in str(got.value) and str(got.value) == str(expected.value)
    assert not (tmp_path / "out.parquet").exists()  # không để lại file dở


def test_streaming_enforces_row_and_column_limits(tmp_path, monkeypatch):
    source = tmp_path / "in.csv"
    source.write_text("a,b\n" + "\n".join(f"{i},x" for i in range(10)), encoding="utf-8")
    monkeypatch.setattr(settings, "MAX_UPLOAD_ROWS", 5)
    with pytest.raises(ValidationAppError, match="quá"):
        stream_csv_to_parquet(source, tmp_path / "out.parquet", chunk_rows=3)
    assert not (tmp_path / "out.parquet").exists()
    monkeypatch.setattr(settings, "MAX_UPLOAD_ROWS", 1000)
    monkeypatch.setattr(settings, "MAX_UPLOAD_COLUMNS", 1)
    with pytest.raises(ValidationAppError, match="cột"):
        stream_csv_to_parquet(source, tmp_path / "out.parquet")


def test_streaming_leaves_no_temp_files_next_to_the_output(tmp_path):
    source = tmp_path / "in.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    stream_csv_to_parquet(source, tmp_path / "out.parquet")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.csv", "out.parquet"]
