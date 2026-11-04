"""Tầng lưu trữ: driver local (an toàn đường dẫn, ghi nguyên tử) và driver S3 (client giả)."""

from pathlib import Path

import pandas as pd
import pytest

from app.core.config import settings
from app.services import storage


def test_backend_selection(monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "")
    monkeypatch.setattr(settings, "STORAGE_ENDPOINT", "")
    assert storage.get_backend_name() == "local"
    monkeypatch.setattr(settings, "STORAGE_ENDPOINT", "https://s3.example.com")
    assert storage.get_backend_name() == "s3"
    monkeypatch.setattr(settings, "STORAGE_ENDPOINT", "https://<project>.supabase.co/storage/v1/s3")
    assert storage.get_backend_name() == "local"  # giá trị mẫu chưa điền không tính là cấu hình
    monkeypatch.setattr(settings, "STORAGE_ENDPOINT", "https://s3.example.com")
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")  # cấu hình tường minh thắng
    assert storage.get_backend_name() == "local"


def test_bytes_roundtrip_and_overwrite():
    storage.save_bytes("datasets/1/original.csv", b"a,b\n1,2\n")
    assert storage.load_bytes("datasets/1/original.csv") == b"a,b\n1,2\n"
    storage.save_bytes("datasets/1/original.csv", b"moi")
    assert storage.load_bytes("datasets/1/original.csv") == b"moi"


def test_missing_file_raises():
    with pytest.raises(storage.StorageError):
        storage.load_bytes("datasets/9/v1.parquet")


@pytest.mark.parametrize(
    "key",
    [
        "../ngoai.txt",
        "datasets/../../ngoai.txt",
        "/etc/passwd",
        "",
        "a/../../b",
        "C:/x",
        "c:x",
        "datasets/1/a:b",
    ],
)
def test_unsafe_keys_are_rejected(key):
    with pytest.raises(storage.StorageError):
        storage.save_bytes(key, b"x")
    with pytest.raises(storage.StorageError):
        storage.load_bytes(key)


def test_save_does_not_leave_temp_files():
    storage.save_bytes("datasets/2/v1.parquet", b"x")
    files = [p.name for p in Path(settings.STORAGE_LOCAL_DIR).rglob("*") if p.is_file()]
    assert files == ["v1.parquet"]


def test_parquet_roundtrip_keeps_text_exactly():
    df = pd.DataFrame(
        {
            "ho_ten": ["  Nguyễn Văn A ", "Trần Thị B", ""],
            "sdt": ["0901234567", "+84 912 345 678", "N/A"],
            "tuoi": ["29", "", "150"],
        }
    )
    storage.save_dataframe_as_parquet(df, storage.version_key(7, 1))
    loaded = storage.load_dataframe_from_parquet(storage.version_key(7, 1))
    pd.testing.assert_frame_equal(loaded, df)
    assert loaded["sdt"][0] == "0901234567"  # số 0 đầu không bị mất


def test_parquet_corrupted_file_raises_storage_error():
    storage.save_bytes("datasets/3/v1.parquet", b"khong phai parquet")
    with pytest.raises(storage.StorageError):
        storage.load_dataframe_from_parquet("datasets/3/v1.parquet")


def test_delete_prefix_removes_only_that_dataset():
    storage.save_bytes("datasets/4/v1.parquet", b"x")
    storage.save_bytes("datasets/4/v2.parquet", b"y")
    storage.save_bytes("datasets/5/v1.parquet", b"z")
    storage.delete_prefix("datasets/4")
    with pytest.raises(storage.StorageError):
        storage.load_bytes("datasets/4/v1.parquet")
    assert storage.load_bytes("datasets/5/v1.parquet") == b"z"
    storage.delete_prefix("datasets/khong-co")  # không lỗi khi không có gì để xóa


def test_standard_keys():
    assert storage.version_key(3, 2) == "datasets/3/v2.parquet"
    assert storage.original_key(3, "xlsx") == "datasets/3/original.xlsx"
    with pytest.raises(storage.StorageError):
        storage.original_key(3, "exe")


class _FakeS3:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, Bucket, Key, Body):  # noqa: N803  (đúng tên tham số của boto3)
        self.objects[Key] = Body

    def get_object(self, Bucket, Key):  # noqa: N803
        class _Body:
            def read(self_inner):
                return self.objects[Key]

        return {"Body": _Body()}

    def list_objects_v2(self, Bucket, Prefix):  # noqa: N803
        return {"Contents": [{"Key": k} for k in self.objects if k.startswith(Prefix)]}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self.objects.pop(Key, None)


def test_s3_driver_uses_client(monkeypatch):
    fake = _FakeS3()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "s3")
    monkeypatch.setattr(storage, "_get_s3_client", lambda: fake)
    storage.save_bytes("datasets/1/original.csv", b"abc")
    assert fake.objects == {"datasets/1/original.csv": b"abc"}
    assert storage.load_bytes("datasets/1/original.csv") == b"abc"
    storage.delete_prefix("datasets/1")
    assert fake.objects == {}
    with pytest.raises(storage.StorageError):
        storage.load_bytes("datasets/1/original.csv")
