"""Đọc file CSV lớn theo từng khối rồi ghi thẳng ra Parquet, không nạp cả file vào bộ nhớ.

Kết quả (tên cột, nội dung từng ô, số dòng) phải GIỐNG HỆT read_csv_file + _build_frame dùng cho
file nhỏ: cùng cách dò encoding, dấu phân cách, dòng tiêu đề, bỏ dòng trống, bỏ cột thừa và đặt tên
cột trùng. Khác biệt duy nhất là đọc theo khối `chunk_rows` dòng, nên có test so sánh hai đường.
"""

import csv
import io
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pandas.errors import EmptyDataError, ParserError

from app.core.config import settings
from app.core.exceptions import ValidationAppError
from app.services.ingestion.delimiter import detect_delimiter
from app.services.ingestion.encoding import detect_encoding
from app.services.ingestion.header_detect import detect_header_row
from app.services.ingestion.reader import _SAMPLE_BYTES, _SAMPLE_LINES, check_file_signature

DEFAULT_CHUNK_ROWS = 100_000
PREVIEW_ROWS = 20
_HEADER_LOOKAHEAD = 10  # detect_header_row chỉ xét 10 dòng đầu


@dataclass
class StreamedCsv:
    """Kết quả đọc theo luồng: file Parquet đã dựng, kích thước bảng, xem trước và encoding."""

    parquet_path: Path
    row_count: int
    columns: list[str]
    preview: pd.DataFrame
    encoding: str


def _blank_mask(raw: pd.DataFrame) -> pd.Series:
    return raw.apply(lambda col: col.str.strip() == "").all(axis=1)


def _unique_names(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    names: list[str] = []
    for position, header in enumerate(headers, start=1):
        base = header or f"cot_{position}"
        seen[base] = seen.get(base, 0) + 1
        names.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return names


def stream_csv_to_parquet(
    source: Path, output: Path, chunk_rows: int = DEFAULT_CHUNK_ROWS
) -> StreamedCsv:
    """Đọc CSV `source` theo khối và ghi Parquet (mọi cột là chuỗi) vào `output`."""
    with source.open("rb") as handle:
        head = handle.read(_SAMPLE_BYTES + 4)  # +4 byte để dò UTF-8 bị cắt giữa ký tự như file nhỏ
    check_file_signature("csv", head)
    encoding = detect_encoding(head)
    delimiter = detect_delimiter(head[:_SAMPLE_BYTES].decode(encoding, errors="replace"))

    width = 0
    sample = head[:_SAMPLE_BYTES].decode(encoding, errors="replace")
    for index, row in enumerate(csv.reader(io.StringIO(sample), delimiter=delimiter)):
        width = max(width, len(row))
        if index >= _SAMPLE_LINES:
            break
    if width == 0:
        raise ValidationAppError("File không có dữ liệu.")
    if width > settings.MAX_UPLOAD_COLUMNS:
        raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_COLUMNS} cột.")

    normalize_nfc = not encoding.lower().replace("_", "-").startswith(("utf-8", "utf8", "ascii"))
    provisional = [f"c{i}" for i in range(width)]
    schema = pa.schema([(name, pa.string()) for name in provisional])

    def to_table(frame: pd.DataFrame) -> pa.Table:
        frame = frame.copy()
        frame.columns = provisional
        return pa.Table.from_pandas(frame, schema=schema, preserve_index=False)

    # Parquet tạm với tên cột c0..cN, ghi lại thành bản cuối ở cuối hàm.
    fd, tmp_name = tempfile.mkstemp(suffix=".parquet", dir=output.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    writer: pq.ParquetWriter | None = None
    reader = None
    try:
        reader = pd.read_csv(
            source,
            header=None,
            names=range(width),
            dtype=str,
            keep_default_na=False,
            encoding=encoding,
            encoding_errors="replace",
            sep=delimiter,
            skip_blank_lines=True,
            chunksize=chunk_rows,
        )
        writer = pq.ParquetWriter(tmp_path, schema)
        headers: list[str] | None = None
        has_data = [False] * width
        rows_written = 0
        pending: list[pd.DataFrame] = []
        pending_rows = 0

        def write_data(data: pd.DataFrame) -> None:
            nonlocal rows_written
            if data.empty:
                return
            rows_written += len(data)
            if rows_written > settings.MAX_UPLOAD_ROWS:
                raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_ROWS:,} dòng.")
            filled = data.apply(lambda col: col.str.strip() != "").any()
            for i in range(width):
                has_data[i] = has_data[i] or bool(filled.iloc[i])
            writer.write_table(to_table(data))

        def start(buffer: pd.DataFrame) -> list[str]:
            header_row = detect_header_row(buffer)
            found = [str(v).strip().lstrip("\ufeff") for v in buffer.iloc[header_row]]
            write_data(buffer.iloc[header_row + 1 :].reset_index(drop=True))
            return found

        for chunk in reader:
            raw = chunk.fillna("").astype(str)
            if normalize_nfc:
                raw = raw.apply(lambda col: col.map(lambda v: unicodedata.normalize("NFC", v)))
            raw = raw[~_blank_mask(raw)].reset_index(drop=True)
            if headers is not None:
                write_data(raw)
                continue
            pending.append(raw)
            pending_rows += len(raw)
            if pending_rows >= _HEADER_LOOKAHEAD:
                headers = start(pd.concat(pending, ignore_index=True))
                pending = []
        if headers is None:
            buffer = pd.concat(pending, ignore_index=True) if pending else pd.DataFrame()
            if buffer.empty:
                raise ValidationAppError("File không có dữ liệu.")
            headers = start(buffer)

        keep = [i for i, h in enumerate(headers) if h or has_data[i]]
        names = _unique_names([headers[i] for i in keep])
        if rows_written == 0 or not names:
            raise ValidationAppError("File không có dữ liệu (chỉ có dòng tiêu đề).")
        if len(names) > settings.MAX_UPLOAD_COLUMNS:
            raise ValidationAppError(f"File có quá {settings.MAX_UPLOAD_COLUMNS} cột.")
        writer.close()
        writer = None

        final_schema = pa.schema([(name, pa.string()) for name in names])
        preview_parts: list[pd.DataFrame] = []
        preview_rows = 0
        with pq.ParquetWriter(output, final_schema) as final:
            for batch in pq.ParquetFile(tmp_path).iter_batches(
                batch_size=chunk_rows, columns=[provisional[i] for i in keep]
            ):
                table = pa.Table.from_batches([batch]).rename_columns(names)
                final.write_table(table)
                if preview_rows < PREVIEW_ROWS:  # gom đủ dòng xem trước dù khối nhỏ hơn
                    preview_parts.append(table.slice(0, PREVIEW_ROWS - preview_rows).to_pandas())
                    preview_rows += len(preview_parts[-1])
        preview = pd.concat(preview_parts, ignore_index=True)
    except ValidationAppError:
        output.unlink(missing_ok=True)
        raise
    except EmptyDataError as exc:
        output.unlink(missing_ok=True)
        raise ValidationAppError("File không có dữ liệu.") from exc
    except (ParserError, UnicodeError, csv.Error, ValueError) as exc:
        output.unlink(missing_ok=True)
        raise ValidationAppError(
            "Không đọc được file CSV: cấu trúc dòng/cột không nhất quán hoặc file bị hỏng."
        ) from exc
    finally:
        if reader is not None:
            reader.close()
        if writer is not None:
            writer.close()
        tmp_path.unlink(missing_ok=True)
    return StreamedCsv(output, rows_written, names, preview, encoding)
