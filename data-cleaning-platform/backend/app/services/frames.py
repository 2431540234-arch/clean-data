"""Đọc DataFrame của một phiên bản dataset từ nơi lưu trữ."""

import io

import pandas as pd
import pyarrow.parquet as pq

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


def load_version_columns(version: DatasetVersion) -> list[str]:
    """Tên các cột của phiên bản (chỉ đọc phần mô tả của file Parquet, không nạp dữ liệu)."""
    try:
        content = storage.load_bytes(version.storage_path)
        return [str(name) for name in pq.ParquetFile(io.BytesIO(content)).schema_arrow.names]
    except storage.StorageError as exc:
        raise NotFoundError(
            "Không đọc được dữ liệu của phiên bản này (file lưu trữ bị mất)."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - file Parquet hỏng
        raise NotFoundError("File dữ liệu của phiên bản này bị hỏng.") from exc


def load_version_rows(
    version: DatasetVersion, offset: int, limit: int
) -> tuple[list[str], int, list[dict[str, str | None]]]:
    """(tên cột, tổng số dòng, các dòng offset..offset+limit) của phiên bản; ô trống -> None."""
    try:
        table = pq.read_table(io.BytesIO(storage.load_bytes(version.storage_path)))
    except storage.StorageError as exc:
        raise NotFoundError(
            "Không đọc được dữ liệu của phiên bản này (file lưu trữ bị mất)."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - file Parquet hỏng
        raise NotFoundError("File dữ liệu của phiên bản này bị hỏng.") from exc
    page = table.slice(offset, limit).to_pylist()
    rows = [{k: (None if v in (None, "") else str(v)) for k, v in row.items()} for row in page]
    return [str(n) for n in table.schema.names], table.num_rows, rows
