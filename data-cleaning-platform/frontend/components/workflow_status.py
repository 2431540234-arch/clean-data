"""Trạng thái từng bước của quy trình làm sạch, tính từ dữ liệu thật của dataset đang chọn.

Hàm thuần (không gọi Streamlit/API) để kiểm thử trực tiếp. Quy tắc:
  - upload      Xong khi đã chọn dataset.
  - overview    Xong khi phiên bản hiện tại đã được phân tích (profiling).
  - mapping     Xong khi có phiên bản nào đã áp dụng bước "Đổi tên cột"; Đang làm khi còn bước
                đổi tên chờ áp dụng (đã xác nhận mapping nhưng chưa áp dụng).
  - suggestions Xong khi đã áp dụng làm sạch ít nhất một lần (dataset có từ 2 phiên bản).
  - history     Xong khi dataset có từ 2 phiên bản (có lịch sử để xem, hoàn tác, khôi phục).
  - export      Xong khi đã từng xuất dataset này (theo nhật ký hoạt động).
Chưa chọn dataset thì mọi bước là "Chưa làm". "Đang làm" là bước đầu tiên chưa xong mà phía sau nó
chưa có bước nào xong (bước bị bỏ qua, như mapping, vẫn là "Chưa làm").
"""

from typing import Any

DONE = "Xong"
DOING = "Đang làm"
TODO = "Chưa làm"

_ORDER = ("upload", "overview", "mapping", "suggestions", "history", "export")
_RENAME_LABEL = (
    "Đổi tên cột"  # khớp OP_LABELS["rename_column"] của backend (services/versioning.py)
)


def workflow_status(
    *,
    has_dataset: bool,
    profiled: bool,
    versions: list[dict[str, Any]],
    exported: bool,
    mapping_pending: bool = False,
) -> dict[str, str]:
    """Trạng thái (Xong / Đang làm / Chưa làm) của từng bước theo khóa trang."""
    if not has_dataset:
        return {key: TODO for key in _ORDER}
    renamed = any(_RENAME_LABEL in (v.get("change_summary") or "") for v in versions)
    cleaned = len(versions) > 1
    done = {
        "upload": True,
        "overview": profiled,
        "mapping": renamed,
        "suggestions": cleaned,
        "history": cleaned,
        "export": exported,
    }
    status = {key: DONE if done[key] else TODO for key in _ORDER}
    for index, key in enumerate(_ORDER):
        if not done[key] and not any(done[later] for later in _ORDER[index + 1 :]):
            status[key] = DOING
            break
    if mapping_pending and not done["mapping"]:
        status["mapping"] = DOING
    return status
