"""Nhãn tiếng Việt cho các giá trị kỹ thuật trả về từ backend."""

# Khớp INFERRED_TYPES của backend/app/services/profiling/type_inference.py.
TYPE_LABELS = {
    "integer": "Số nguyên",
    "float": "Số thực",
    "date": "Ngày",
    "phone": "Điện thoại",
    "email": "Email",
    "boolean": "Đúng/Sai",
    "text": "Văn bản",
}


def type_label(inferred_type: str) -> str:
    """Nhãn tiếng Việt của kiểu dữ liệu suy luận; kiểu lạ giữ nguyên."""
    return TYPE_LABELS.get(inferred_type, inferred_type)


# Khớp ALLOWED_OPS của backend/app/schemas/rule.py.
OP_LABELS = {
    "trim_whitespace": "Cắt khoảng trắng thừa",
    "change_case": "Đổi chữ hoa/thường",
    "replace_values": "Thay thế giá trị",
    "standardize_date": "Chuẩn hóa ngày",
    "standardize_phone": "Chuẩn hóa số điện thoại",
    "standardize_email": "Chuẩn hóa email",
    "cast_type": "Ép kiểu dữ liệu",
    "fill_missing": "Điền giá trị thiếu",
    "drop_duplicates": "Xóa dòng trùng lặp",
    "drop_rows_where": "Xóa dòng theo điều kiện",
    "flag_outliers": "Đánh dấu giá trị bất thường",
    "rename_column": "Đổi tên cột",
    "drop_column": "Xóa cột",
}

# Khớp SuggestionOut.status / source.
STATUS_LABELS = {"pending": "Chưa duyệt", "accepted": "Đã chấp nhận", "rejected": "Đã từ chối"}
SOURCE_LABELS = {"ai": "AI đề xuất", "rule_engine": "Quy tắc"}


def op_label(op: str) -> str:
    """Nhãn tiếng Việt của một op rule; op lạ giữ nguyên."""
    return OP_LABELS.get(op, op)


def describe_step(step: dict) -> str:
    """Mô tả ngắn một RuleStep cho người dùng, ví dụ: Chuẩn hóa ngày — cột “ngay_sinh”."""
    op, column = step["op"], step.get("column")
    if op == "rename_column":
        new_name = (step.get("params") or {}).get("new_name", "?")
        return f"Đổi tên cột “{column}” thành “{new_name}”"
    label = op_label(op)
    return f"{label} — cột “{column}”" if column else f"{label} (toàn bộ bảng)"


# Mã hành động nhật ký. Backend chỉ nêu ví dụ ("dataset.upload", "version.apply_rule", "user.lock")
# trong app/services/audit.py; mã lạ hiển thị nguyên văn nên thêm mã mới không làm hỏng giao diện.
ACTION_LABELS = {
    "dataset.upload": "Tải lên dataset",
    "dataset.export": "Xuất dữ liệu",
    "project.create": "Tạo project",
    "project.update": "Đổi tên project",
    "project.delete": "Xóa project",
    "suggestion.accept": "Chấp nhận gợi ý",
    "suggestion.reject": "Từ chối gợi ý",
    "version.apply_rule": "Áp dụng rule",
    "version.undo": "Hoàn tác phiên bản",
    "version.redo": "Làm lại phiên bản",
    "version.restore": "Khôi phục phiên bản",
    "auth.change_password": "Đổi mật khẩu",
    "auth.login": "Đăng nhập",
    "auth.login_failed": "Đăng nhập thất bại",
    "auth.register": "Đăng ký tài khoản",
    "suggestion.generate": "Sinh gợi ý làm sạch",
    "dataset.select_sheet": "Chọn lại sheet Excel",
    "rule.create": "Lưu rule mẫu",
    "rule.delete": "Xóa rule mẫu",
    "user.lock": "Khóa tài khoản",
    "user.unlock": "Mở khóa tài khoản",
    "user.change_role": "Đổi quyền",
    "user.reset_password": "Đặt lại mật khẩu",
}
ENTITY_LABELS = {
    "dataset": "Dataset",
    "project": "Project",
    "suggestion": "Gợi ý",
    "user": "Người dùng",
    "system": "Hệ thống",
}


def action_label(action: str) -> str:
    """Nhãn tiếng Việt của mã hành động; mã lạ giữ nguyên."""
    return ACTION_LABELS.get(action, action)


def entity_label(entity_type: str, entity_id: int | None) -> str:
    """Ví dụ "Dataset #1"; không có id thì chỉ tên loại."""
    name = ENTITY_LABELS.get(entity_type, entity_type)
    return f"{name} #{entity_id}" if entity_id is not None else name


ROLE_LABELS = {"admin": "Quản trị viên", "user": "Người dùng"}


def role_label(role: str) -> str:
    """Nhãn tiếng Việt của quyền; quyền lạ giữ nguyên."""
    return ROLE_LABELS.get(role, role)


# Khớp DataIssueOut.severity / issue_type của backend.
SEVERITY_LABELS = {"high": "Cao", "medium": "Trung bình", "low": "Thấp"}
SEVERITY_KIND = {"high": "error", "medium": "warning", "low": "neutral"}
SEVERITY_COLORS = {"high": "#DC2626", "medium": "#D97706", "low": "#94A3B8"}
ISSUE_TYPE_LABELS = {
    "duplicate": "Trùng lặp",
    "missing": "Thiếu dữ liệu",
    "outlier": "Giá trị bất thường",
    "invalid_format": "Sai định dạng",
    "type_mismatch": "Sai kiểu dữ liệu",
    "inconsistent": "Không nhất quán",
}


def severity_label(severity: str) -> str:
    """Nhãn tiếng Việt của mức độ nghiêm trọng; mức lạ giữ nguyên."""
    return SEVERITY_LABELS.get(severity, severity)


def issue_type_label(issue_type: str) -> str:
    """Nhãn tiếng Việt của loại lỗi; loại lạ giữ nguyên."""
    return ISSUE_TYPE_LABELS.get(issue_type, issue_type)
