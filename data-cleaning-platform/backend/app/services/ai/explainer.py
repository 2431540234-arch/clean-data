"""Giải thích lỗi dữ liệu bằng tiếng Việt dễ hiểu cho người dùng không chuyên kỹ thuật."""

from app.services.detectors.base import DetectionIssue

# Giải thích theo mã kind của detector: vì sao đây là vấn đề (không cần gọi AI cho việc này).
_TEMPLATES: dict[str, str] = {
    "missing_values": (
        "Cột '{col}' còn ô trống hoặc ghi dấu thay thế như 'N/A', '-'. Ô thiếu làm các thống "
        "kê và báo cáo dựa trên cột này kém chính xác."
    ),
    "exact_duplicate_rows": (
        "Có những dòng giống hệt dòng khác. Dòng lặp làm đếm thừa (ví dụ một khách hàng bị tính "
        "hai lần) và làm sai tổng hợp."
    ),
    "near_duplicate_rows": (
        "Có những dòng gần như giống nhau, chỉ khác khoảng trắng, hoa/thường hoặc lỗi gõ nhẹ, "
        "nhiều khả năng là cùng một đối tượng nhập hai lần."
    ),
    "iqr_outlier": (
        "Cột '{col}' có giá trị nằm quá xa phần lớn dữ liệu (ví dụ tuổi 150). Đó thường là lỗi "
        "nhập liệu và làm lệch trung bình."
    ),
    "non_numeric_in_numeric": (
        "Cột '{col}' chủ yếu là số nhưng có vài ô chứa chữ. Các ô này làm cột không tính toán "
        "hoặc sắp xếp theo số được."
    ),
    "mixed_date_format": (
        "Cột '{col}' ghi ngày theo nhiều cách khác nhau (ví dụ 15/04/1990 lẫn 1990-04-15). Máy "
        "không so sánh hay sắp xếp theo ngày đúng được khi định dạng lẫn lộn."
    ),
    "invalid_date": (
        "Cột '{col}' có giá trị trông giống ngày nhưng không phải ngày có thật (ví dụ 31/02). "
        "Cần người kiểm tra lại với nguồn gốc."
    ),
    "mixed_phone_format": (
        "Cột '{col}' viết số điện thoại theo nhiều kiểu (có/không khoảng trắng, +84 hoặc 0). "
        "Cùng một số có thể bị coi là hai số khác nhau."
    ),
    "invalid_phone": (
        "Cột '{col}' có số điện thoại không đúng dạng số Việt Nam (thiếu hoặc thừa chữ số). "
        "Cần người kiểm tra lại với nguồn gốc."
    ),
    "invalid_email": (
        "Cột '{col}' có địa chỉ email sai cú pháp (thiếu @ hoặc tên miền). Email sai không "
        "gửi thư được."
    ),
    "email_case_whitespace": (
        "Cột '{col}' có email thừa khoảng trắng hoặc viết hoa. Cùng một email có thể bị coi là "
        "hai địa chỉ khác nhau khi đối chiếu."
    ),
    "extra_whitespace": (
        "Cột '{col}' có giá trị thừa khoảng trắng đầu/cuối hoặc nhiều khoảng trắng liền nhau. "
        "Nhìn thì giống nhau nhưng máy coi là khác nhau."
    ),
    "mixed_case": (
        "Cột '{col}' viết hoa/thường không thống nhất, nên cùng một giá trị có thể bị tách "
        "thành nhiều nhóm."
    ),
    "value_variants": (
        "Cột '{col}' dùng nhiều cách viết khác nhau cho cùng một giá trị (ví dụ 'HCM', "
        "'TP.HCM', 'Hồ Chí Minh'). Thống kê theo nhóm sẽ bị chia nhỏ sai."
    ),
}


def explain_issue(issue: DetectionIssue) -> str:
    """Mô tả tiếng Việt dễ hiểu cho một lỗi: vì sao nó là vấn đề (dựa trên mẫu có sẵn)."""
    template = _TEMPLATES.get(str(issue.extra.get("kind")))
    if template is None:
        return issue.message
    return template.format(col=issue.column or "")
