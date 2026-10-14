"""Mapping cột tầng 1: fuzzy matching giữa tên cột trong file upload và schema mong muốn."""


def match_columns(source_columns: list[str], target_schema: list[str]) -> dict[str, str | None]:
    """Gợi ý mapping cột nguồn -> cột đích bằng kết hợp synonyms + fuzzy matching.

    Gợi ý cách làm:
    1. Chuẩn hóa từng cột nguồn bằng app.services.mapping.normalizer.normalize_column_name.
    2. Thử tra từ điển đồng nghĩa (app.services.mapping.synonyms.find_canonical_name).
    3. Nếu không tìm thấy, dùng rapidfuzz.process.extractOne để so khớp với target_schema,
       chỉ nhận nếu điểm khớp vượt ngưỡng (ví dụ >= 80).
    4. Cột không khớp được trả về None (sẽ được xử lý ở tầng 2 bằng AI).
    """
    raise NotImplementedError(
        "TODO: kết hợp normalizer + synonyms + rapidfuzz để mapping cột tầng 1."
    )
