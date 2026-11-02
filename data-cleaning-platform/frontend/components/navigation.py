"""Danh mục trang của ứng dụng: nguồn duy nhất cho menu, stepper và các nút dẫn trang."""

from dataclasses import dataclass

import streamlit as st

PRODUCT_NAME = "Data Cleaning Platform"
PRODUCT_SHORT_NAME = "DataClean"  # TODO: đổi nếu chốt tên ngắn khác (hiện dùng ở sidebar/logo)
PRODUCT_TAGLINE = "Nền tảng làm sạch dữ liệu Excel/CSV có AI gợi ý chuẩn hóa"


@dataclass(frozen=True)
class PageDef:
    """Khai báo một trang: file trong views/, tiêu đề, icon, nhóm menu, quyền."""

    key: str
    file: str
    title: str
    icon: str
    url_path: str
    group: str | None
    admin_only: bool = False
    default: bool = False


GROUP_OVERVIEW = "Tổng quan"
GROUP_FLOW = "Quy trình làm sạch"
GROUP_ACCOUNT = "Cá nhân"
GROUP_ADMIN = "Quản trị"

PAGES: tuple[PageDef, ...] = (
    PageDef("login", "views/login.py", "Đăng nhập", "login", "dang-nhap", None, default=True),
    PageDef("home", "views/home.py", "Trang chủ", "home", "", GROUP_OVERVIEW, default=True),
    PageDef(
        "dashboard", "views/dashboard.py", "Dashboard", "dashboard", "dashboard", GROUP_OVERVIEW
    ),
    PageDef("upload", "views/upload.py", "Tải lên", "upload_file", "tai-len", GROUP_FLOW),
    PageDef(
        "overview",
        "views/overview.py",
        "Tổng quan dữ liệu",
        "query_stats",
        "tong-quan-du-lieu",
        GROUP_FLOW,
    ),
    PageDef("mapping", "views/mapping.py", "Mapping cột", "swap_horiz", "mapping-cot", GROUP_FLOW),
    PageDef(
        "suggestions",
        "views/suggestions.py",
        "Gợi ý làm sạch",
        "auto_fix_high",
        "goi-y-lam-sach",
        GROUP_FLOW,
    ),
    PageDef(
        "history",
        "views/history.py",
        "Lịch sử phiên bản",
        "history",
        "lich-su-phien-ban",
        GROUP_FLOW,
    ),
    PageDef("export", "views/export.py", "Xuất dữ liệu", "download", "xuat-du-lieu", GROUP_FLOW),
    PageDef(
        "audit",
        "views/audit.py",
        "Nhật ký hoạt động",
        "receipt_long",
        "nhat-ky-hoat-dong",
        GROUP_ACCOUNT,
    ),
    PageDef(
        "account", "views/account.py", "Tài khoản", "account_circle", "tai-khoan", GROUP_ACCOUNT
    ),
    PageDef(
        "admin_users",
        "views/admin_users.py",
        "Quản trị người dùng",
        "admin_panel_settings",
        "quan-tri-nguoi-dung",
        GROUP_ADMIN,
        admin_only=True,
    ),
    PageDef(
        "admin_stats",
        "views/admin_stats.py",
        "Thống kê hệ thống",
        "monitoring",
        "thong-ke-he-thong",
        GROUP_ADMIN,
        admin_only=True,
    ),
)

# Thứ tự các bước trong luồng làm sạch (theo phụ thuộc của backend: có profiling mới sinh
# được gợi ý; mapping chỉ cần version; đổi tên cột đi qua rule rename_column nên làm trước).
FLOW_KEYS: tuple[str, ...] = (
    "upload",
    "overview",
    "mapping",
    "suggestions",
    "history",
    "export",
)

_BY_KEY = {page.key: page for page in PAGES}


def get_page(key: str) -> PageDef:
    """Lấy khai báo trang theo key."""
    return _BY_KEY[key]


def build_pages(logged_in: bool, admin: bool) -> list[st.Page] | dict[str, list[st.Page]]:
    """Dựng danh sách st.Page cho st.navigation theo trạng thái đăng nhập và quyền."""
    if not logged_in:
        return [_to_st_page(_BY_KEY["login"])]

    sections: dict[str, list[st.Page]] = {}
    for page in PAGES:
        if page.key == "login" or (page.admin_only and not admin):
            continue
        sections.setdefault(page.group or "", []).append(_to_st_page(page))
    return sections


def _to_st_page(page: PageDef) -> st.Page:
    return st.Page(
        page.file,
        title=page.title,
        icon=f":material/{page.icon}:",
        url_path=page.url_path or None,
        default=page.default,
    )
