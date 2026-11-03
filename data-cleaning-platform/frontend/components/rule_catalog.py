"""Danh mục quy tắc hệ thống dùng chung, khớp mã op trong docs/rule_dsl.md."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SystemRuleDef:
    """Định nghĩa một quy tắc chuẩn trong thư viện hệ thống."""

    id: str
    name: str
    description: str
    category: str  # "Văn bản", "Định dạng", "Thiếu, trùng, ngoại lai", "Cấu trúc cột"
    op: str
    requires_column: bool
    default_params: dict[str, Any] = field(default_factory=dict)
    param_schema: dict[str, Any] = field(default_factory=dict)
    icon: str = "auto_fix_normal"


SYSTEM_RULE_CATEGORIES: tuple[str, ...] = (
    "Văn bản",
    "Định dạng",
    "Thiếu, trùng, ngoại lai",
    "Cấu trúc cột",
)

SYSTEM_RULES: tuple[SystemRuleDef, ...] = (
    # --- 1. Nhóm Văn bản ---
    SystemRuleDef(
        id="trim_whitespace",
        name="Xóa khoảng trắng thừa",
        description="Cắt khoảng trắng đầu/cuối và gộp khoảng trắng kép",
        category="Văn bản",
        op="trim_whitespace",
        requires_column=True,
        default_params={},
        icon="format_align_left",
    ),
    SystemRuleDef(
        id="change_case",
        name="Đổi kiểu chữ",
        description="Chuyển thành chữ HOA, chữ thường hoặc Viết Hoa Chữ Đầu",
        category="Văn bản",
        op="change_case",
        requires_column=True,
        default_params={"mode": "title"},
        param_schema={
            "mode": {
                "label": "Kiểu chữ",
                "type": "select",
                "options": [
                    ("title", "Viết Hoa Chữ Đầu (Title Case)"),
                    ("upper", "CHỮ HOA (UPPERCASE)"),
                    ("lower", "chữ thường (lowercase)"),
                ],
            }
        },
        icon="text_fields",
    ),
    SystemRuleDef(
        id="replace_values",
        name="Thay thế giá trị",
        description="Thay một hoặc nhiều cặp giá trị cũ → mới",
        category="Văn bản",
        op="replace_values",
        requires_column=True,
        default_params={"mapping": {}},
        param_schema={"mapping": {"label": "Cặp giá trị (cũ → mới)", "type": "mapping"}},
        icon="find_replace",
    ),
    # --- 2. Nhóm Định dạng ---
    SystemRuleDef(
        id="standardize_date",
        name="Chuẩn hóa ngày",
        description="Đưa về định dạng chuẩn dd/mm/yyyy hoặc yyyy-mm-dd",
        category="Định dạng",
        op="standardize_date",
        requires_column=True,
        default_params={"output_format": "%d/%m/%Y", "dayfirst": True},
        param_schema={
            "output_format": {
                "label": "Định dạng đích",
                "type": "select",
                "options": [
                    ("%d/%m/%Y", "dd/mm/yyyy (Ví dụ: 15/04/1990)"),
                    ("%Y-%m-%d", "yyyy-mm-dd (Ví dụ: 1990-04-15)"),
                ],
            },
            "dayfirst": {"label": "Ưu tiên ngày trước tháng", "type": "bool", "default": True},
        },
        icon="calendar_today",
    ),
    SystemRuleDef(
        id="standardize_phone",
        name="Chuẩn hóa số điện thoại",
        description="Đưa số điện thoại về chuẩn 0xxxxxxxxx (chuẩn quốc gia VN)",
        category="Định dạng",
        op="standardize_phone",
        requires_column=True,
        default_params={"region": "VN", "output_format": "national"},
        param_schema={
            "region": {"label": "Khu vực", "type": "select", "options": [("VN", "Việt Nam (VN)")]},
            "output_format": {
                "label": "Định dạng",
                "type": "select",
                "options": [
                    ("national", "Số nội địa 0xxxxxxxxx"),
                    ("e164", "Chuẩn quốc tế +84xxxxxxxxx"),
                ],
            },
        },
        icon="call",
    ),
    SystemRuleDef(
        id="standardize_email",
        name="Kiểm tra email",
        description="Đánh dấu hoặc chuẩn hóa định dạng email",
        category="Định dạng",
        op="standardize_email",
        requires_column=True,
        default_params={"drop_invalid": False},
        param_schema={
            "drop_invalid": {"label": "Xóa ô email không hợp lệ", "type": "bool", "default": False}
        },
        icon="mail",
    ),
    SystemRuleDef(
        id="cast_type",
        name="Ép kiểu dữ liệu",
        description="Chuyển kiểu dữ liệu sang số nguyên, số thực, ngày hoặc chữ",
        category="Định dạng",
        op="cast_type",
        requires_column=True,
        default_params={"target_type": "str", "on_error": "coerce"},
        param_schema={
            "target_type": {
                "label": "Kiểu dữ liệu đích",
                "type": "select",
                "options": [
                    ("int", "Số nguyên (int)"),
                    ("float", "Số thực (float)"),
                    ("str", "Văn bản (str)"),
                    ("datetime", "Ngày giờ (datetime)"),
                ],
            },
            "on_error": {
                "label": "Khi gặp lỗi chuyển đổi",
                "type": "select",
                "options": [
                    ("coerce", "Chuyển thành giá trị trống (NaN)"),
                    ("ignore", "Giữ nguyên giá trị cũ"),
                ],
            },
        },
        icon="transform",
    ),
    # --- 3. Nhóm Thiếu, trùng, ngoại lai ---
    SystemRuleDef(
        id="fill_missing",
        name="Điền giá trị thiếu",
        description="Điền ô trống bằng hằng số, trung bình, trung vị hoặc phổ biến",
        category="Thiếu, trùng, ngoại lai",
        op="fill_missing",
        requires_column=True,
        default_params={"strategy": "constant", "value": ""},
        param_schema={
            "strategy": {
                "label": "Phương pháp điền",
                "type": "select",
                "options": [
                    ("constant", "Hằng số tùy chọn"),
                    ("mean", "Giá trị trung bình (Mean)"),
                    ("median", "Giá trị trung vị (Median)"),
                    ("mode", "Giá trị xuất hiện nhiều nhất (Mode)"),
                ],
            },
            "value": {"label": "Giá trị điền (nếu chọn hằng số)", "type": "str", "default": ""},
        },
        icon="edit_note",
    ),
    SystemRuleDef(
        id="drop_duplicates",
        name="Xóa dòng trùng lặp",
        description="Xóa bản ghi trùng theo cả dòng hoặc theo cột khóa",
        category="Thiếu, trùng, ngoại lai",
        op="drop_duplicates",
        requires_column=False,
        default_params={"subset": None, "keep": "first"},
        param_schema={
            "keep": {
                "label": "Dòng giữ lại",
                "type": "select",
                "options": [
                    ("first", "Giữ dòng xuất hiện đầu tiên"),
                    ("last", "Giữ dòng xuất hiện sau cùng"),
                ],
            }
        },
        icon="content_copy",
    ),
    SystemRuleDef(
        id="drop_rows_where",
        name="Xóa dòng theo điều kiện",
        description="Xóa các dòng có giá trị thỏa điều kiện trên cột được chọn",
        category="Thiếu, trùng, ngoại lai",
        op="drop_rows_where",
        requires_column=True,
        default_params={"operator": "eq", "value": ""},
        param_schema={
            "operator": {
                "label": "Điều kiện",
                "type": "select",
                "options": [
                    ("gt", "Lớn hơn"),
                    ("lt", "Nhỏ hơn"),
                    ("gte", "Lớn hơn hoặc bằng"),
                    ("lte", "Nhỏ hơn hoặc bằng"),
                    ("eq", "Bằng"),
                    ("neq", "Khác"),
                    ("is_null", "Đang trống"),
                    ("is_not_null", "Không trống"),
                ],
            },
            "value": {"label": "Giá trị so sánh", "type": "str", "default": ""},
        },
        icon="filter_alt",
    ),
    SystemRuleDef(
        id="flag_outliers",
        name="Đánh dấu ngoại lai",
        description="Phát hiện giá trị bất thường bằng thuật toán IQR hoặc Z-score",
        category="Thiếu, trùng, ngoại lai",
        op="flag_outliers",
        requires_column=True,
        default_params={"method": "iqr", "threshold": 1.5},
        param_schema={
            "method": {
                "label": "Phương pháp",
                "type": "select",
                "options": [("iqr", "Biên phân vị IQR"), ("zscore", "Độ lệch chuẩn Z-Score")],
            },
            "threshold": {"label": "Ngưỡng (Threshold)", "type": "float", "default": 1.5},
        },
        icon="priority_high",
    ),
    # --- 4. Nhóm Cấu trúc cột ---
    SystemRuleDef(
        id="rename_column",
        name="Đổi tên cột",
        description="Đổi tên cột sang tên mới chuẩn hóa",
        category="Cấu trúc cột",
        op="rename_column",
        requires_column=True,
        default_params={"new_name": ""},
        param_schema={"new_name": {"label": "Tên cột mới", "type": "str"}},
        icon="drive_file_rename_outline",
    ),
    SystemRuleDef(
        id="drop_column",
        name="Xóa cột",
        description="Xóa bỏ một cột không cần thiết khỏi dataset",
        category="Cấu trúc cột",
        op="drop_column",
        requires_column=True,
        default_params={},
        icon="delete",
    ),
)

SUPPORTED_RULE_OPS: tuple[str, ...] = tuple(rule.op for rule in SYSTEM_RULES)


def get_system_rule(rule_id: str) -> SystemRuleDef | None:
    """Lấy định nghĩa quy tắc theo id."""
    for r in SYSTEM_RULES:
        if r.id == rule_id or r.op == rule_id:
            return r
    return None
