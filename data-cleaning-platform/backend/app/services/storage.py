"""Lưu/đọc file dữ liệu (Parquet) và file gốc upload.

Hai driver, chọn bằng cấu hình (`settings.STORAGE_BACKEND`, rỗng = tự chọn):
  - "local": thư mục trên đĩa (`settings.STORAGE_LOCAL_DIR`), dùng cho dev/demo, không cần khóa.
  - "s3":    S3-compatible (Supabase Storage / Cloudflare R2) qua boto3, khi có STORAGE_ENDPOINT.

Mọi hàm nhận `storage_path` là khóa tương đối do SERVER sinh (ví dụ "datasets/3/v2.parquet"),
không bao giờ lấy từ người dùng. Driver local vẫn kiểm tra để khóa không thoát khỏi thư mục gốc.
"""

import io
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd

from app.core.config import settings


class StorageError(Exception):
    """Lỗi lưu/đọc file (khóa không hợp lệ, file không tồn tại...)."""


def get_backend_name() -> str:
    """Tên driver đang dùng: "local" hoặc "s3"."""
    configured = settings.STORAGE_BACKEND.strip().lower()
    if configured in {"local", "s3"}:
        return configured
    return "s3" if settings.STORAGE_ENDPOINT else "local"


# ---------------------------------------------------------------- khóa và driver local


def _normalize_key(storage_path: str) -> str:
    """Chuẩn hóa khóa; từ chối khóa rỗng, tuyệt đối hoặc chứa '..'."""
    key = PurePosixPath(storage_path.replace("\\", "/"))
    if not storage_path or key.is_absolute() or ".." in key.parts or key.parts[:1] == ("",):
        raise StorageError("Đường dẫn lưu trữ không hợp lệ.")
    return str(key)


def _local_root() -> Path:
    root = Path(settings.STORAGE_LOCAL_DIR)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root  # tương đối so với thư mục backend/
    return root


def _local_path(storage_path: str) -> Path:
    root = _local_root().resolve()
    target = (root / _normalize_key(storage_path)).resolve()
    if root != target and root not in target.parents:
        raise StorageError("Đường dẫn lưu trữ không hợp lệ.")
    return target


# ---------------------------------------------------------------- driver S3


def _get_s3_client() -> Any:
    """Tạo boto3 client trỏ tới STORAGE_ENDPOINT (S3-compatible)."""
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT or None,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY or None,
        aws_secret_access_key=settings.STORAGE_SECRET_KEY or None,
    )


# ---------------------------------------------------------------- API chung


def save_bytes(storage_path: str, content: bytes) -> None:
    """Lưu một khối byte tại `storage_path` (ghi đè nếu đã có)."""
    key = _normalize_key(storage_path)
    if get_backend_name() == "s3":
        _get_s3_client().put_object(Bucket=settings.STORAGE_BUCKET, Key=key, Body=content)
        return
    target = _local_path(key)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    temp.write_bytes(content)
    temp.replace(target)  # ghi nguyên tử: không để lại file dở khi lỗi giữa chừng


def load_bytes(storage_path: str) -> bytes:
    """Đọc nội dung file; ném StorageError nếu không tồn tại."""
    key = _normalize_key(storage_path)
    if get_backend_name() == "s3":
        try:
            response = _get_s3_client().get_object(Bucket=settings.STORAGE_BUCKET, Key=key)
            return response["Body"].read()
        except Exception as exc:  # noqa: BLE001  (lỗi mạng/khóa không tồn tại của boto3)
            raise StorageError("Không đọc được file dữ liệu.") from exc
    target = _local_path(key)
    if not target.is_file():
        raise StorageError("Không tìm thấy file dữ liệu.")
    return target.read_bytes()


def delete_prefix(prefix: str) -> None:
    """Xóa mọi file có khóa bắt đầu bằng `prefix` (dùng khi xóa dataset/project)."""
    key = _normalize_key(prefix.rstrip("/"))
    if get_backend_name() == "s3":
        client = _get_s3_client()
        listing = client.list_objects_v2(Bucket=settings.STORAGE_BUCKET, Prefix=key + "/")
        for item in listing.get("Contents", []):
            client.delete_object(Bucket=settings.STORAGE_BUCKET, Key=item["Key"])
        return
    target = _local_path(key)
    if target.is_dir():
        for path in sorted(target.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        target.rmdir()


def save_dataframe_as_parquet(df: pd.DataFrame, storage_path: str) -> None:
    """Lưu DataFrame thành file Parquet (pyarrow); mọi cột là chuỗi nên giữ nguyên dữ liệu gốc."""
    buffer = io.BytesIO()
    df.astype(str).to_parquet(buffer, engine="pyarrow", index=False)
    save_bytes(storage_path, buffer.getvalue())


def load_dataframe_from_parquet(storage_path: str) -> pd.DataFrame:
    """Đọc file Parquet thành DataFrame (cột kiểu chuỗi, index 0..n-1)."""
    try:
        return pd.read_parquet(io.BytesIO(load_bytes(storage_path)), engine="pyarrow")
    except StorageError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise StorageError("File dữ liệu bị hỏng hoặc không đọc được.") from exc


# ---------------------------------------------------------------- khóa chuẩn của hệ thống


def version_key(dataset_id: int, version_number: int) -> str:
    """Khóa của file Parquet một phiên bản: datasets/{id}/v{n}.parquet."""
    return f"datasets/{dataset_id}/v{version_number}.parquet"


def original_key(dataset_id: int, file_type: str) -> str:
    """Khóa của file gốc người dùng tải lên (để chọn lại sheet): datasets/{id}/original.<đuôi>."""
    if file_type not in {"csv", "xlsx", "xls"}:
        raise StorageError("Loại file không hợp lệ.")
    return f"datasets/{dataset_id}/original.{file_type}"
