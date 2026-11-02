"""Gợi ý mapping cột tầng 1 cho mock_api: từ điển đồng nghĩa + so khớp gần đúng.

Mô phỏng backend/app/services/mapping (synonyms + fuzzy). Tầng 2 (AI) không được mô phỏng:
cột không khớp trả None, giống khi tầng 1 không tìm được cột phù hợp.
"""

import re
import unicodedata
from difflib import SequenceMatcher

# Rút gọn từ backend/app/data/column_synonyms.json.
SYNONYMS = {
    "ho_ten": ["họ tên", "ho ten", "full_name", "fullname", "ten", "tên", "name", "họ và tên"],
    "email": ["mail", "e-mail", "địa chỉ email", "dia chi email"],
    "so_dien_thoai": [
        "sdt", "sđt", "phone", "phone_number", "dien thoai", "điện thoại", "so dt", "mobile",
    ],
    "ngay_sinh": ["birthday", "birth_date", "date_of_birth", "dob", "ngay sinh"],
    "dia_chi": ["address", "dia chi", "địa chỉ", "noi o", "nơi ở"],
    "tinh_thanh": [
        "province", "city", "tinh", "tỉnh", "thanh pho", "thành phố", "tinh/thanh pho",
    ],
    "gioi_tinh": ["gender", "sex", "gioi tinh"],
    "tuoi": ["age", "tuổi"],
    "chuc_vu": ["position", "job_title", "chuc vu", "chức vụ"],
    "phong_ban": ["department", "phong ban", "phòng ban"],
    "luong": ["salary", "income", "lương", "thu nhap", "thu nhập"],
    "ma_khach_hang": ["customer_id", "customer_code", "ma kh", "mã khách hàng", "ma_kh"],
    "ma_nhan_vien": ["employee_id", "employee_code", "ma nv", "mã nhân viên", "ma_nv"],
    "ngay_tao": ["created_at", "created_date", "ngay tao", "ngày tạo"],
}  # fmt: skip

_FUZZY_THRESHOLD = 0.8


def _key(name: str) -> str:
    """Bỏ dấu tiếng Việt, hạ chữ thường, chỉ giữ chữ-số: dùng để so khớp tên cột."""
    text = unicodedata.normalize("NFD", name.replace("đ", "d").replace("Đ", "D"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9]", "", text.lower())


_CANONICAL_BY_KEY = {
    _key(alias): canonical
    for canonical, aliases in SYNONYMS.items()
    for alias in [canonical, *aliases]
}


def suggest_mapping(source_columns: list[str], target_schema: list[str]) -> dict[str, str | None]:
    """Cột nguồn -> cột đích (None nếu không khớp), giữ thứ tự cột nguồn."""
    targets_by_key = {_key(target): target for target in target_schema}
    result: dict[str, str | None] = {}
    for source in source_columns:
        key = _key(source)
        match = targets_by_key.get(key)  # đã trùng tên chuẩn (bỏ dấu, hoa/thường)
        if match is None:
            canonical = _CANONICAL_BY_KEY.get(key)
            match = targets_by_key.get(_key(canonical)) if canonical else None
        if match is None and key:
            best = max(
                targets_by_key.items(),
                key=lambda item: SequenceMatcher(None, key, item[0]).ratio(),
                default=None,
            )
            if best and SequenceMatcher(None, key, best[0]).ratio() >= _FUZZY_THRESHOLD:
                match = best[1]
        result[source] = match
    return result
