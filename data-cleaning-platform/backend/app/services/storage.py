"""Lưu/đọc file dữ liệu (Parquet) trên S3-compatible storage (Supabase Storage / Cloudflare R2)."""

import pandas as pd


def _get_s3_client():
    """Tạo boto3 client trỏ tới STORAGE_ENDPOINT (S3-compatible).

    Gợi ý cách làm: boto3.client("s3", endpoint_url=settings.STORAGE_ENDPOINT,
    aws_access_key_id=settings.STORAGE_ACCESS_KEY,
    aws_secret_access_key=settings.STORAGE_SECRET_KEY).
    """
    raise NotImplementedError("TODO: tạo boto3 client trỏ tới storage S3-compatible.")


def save_dataframe_as_parquet(df: pd.DataFrame, storage_path: str) -> None:
    """Lưu DataFrame thành file Parquet (pyarrow) và upload lên bucket STORAGE_BUCKET.

    Gợi ý cách làm: df.to_parquet(buffer, engine="pyarrow") rồi
    s3_client.put_object(Bucket=settings.STORAGE_BUCKET, Key=storage_path, Body=buffer.getvalue()).
    """
    raise NotImplementedError("TODO: lưu df thành Parquet và upload lên storage.")


def load_dataframe_from_parquet(storage_path: str) -> pd.DataFrame:
    """Tải file Parquet từ storage và đọc thành DataFrame.

    Gợi ý cách làm: s3_client.get_object(...) lấy bytes, dùng pandas.read_parquet(buffer).
    """
    raise NotImplementedError("TODO: tải file Parquet từ storage và đọc thành DataFrame.")
