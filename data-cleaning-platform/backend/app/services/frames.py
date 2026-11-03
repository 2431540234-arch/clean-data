"""Đọc DataFrame của một phiên bản dataset từ nơi lưu trữ."""

import pandas as pd

from app.core.exceptions import NotFoundError
from app.models.dataset import DatasetVersion
from app.services import storage


def load_version_frame(version: DatasetVersion) -> pd.DataFrame:
    """DataFrame (toàn bộ ô là chuỗi) của phiên bản; file lưu trữ mất/hỏng -> 404 rõ ràng."""
    try:
        return storage.load_dataframe_from_parquet(version.storage_path)
    except storage.StorageError as exc:
        raise NotFoundError(
            "Không đọc được dữ liệu của phiên bản này (file lưu trữ bị mất)."
        ) from exc
