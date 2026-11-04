"""Danh mục trang của ứng dụng: nguồn duy nhất cho menu, stepper và các nút dẫn trang."""

from dataclasses import dataclass

import streamlit as st

PRODUCT_NAME = "Data Cleaning Platform"
PRODUCT_SHORT_NAME = "DataClean"
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
    PageDef("dashboard", "views/dashboard.py", "Dự án", "dashboard", "dashboard", GROUP_OVERVIEW),
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
        "Làm sạch dữ liệu",
        "auto_fix_high",
        "lam-sach-du-lieu",
        GROUP_FLOW,
    ),
    PageDef(
        "rule_library",
        "views/rule_library.py",
        "Thư viện quy tắc",
        "library_books",
        "thu-vien-quy-tac",
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

# Thứ tự các bước trong luồng làm sạch
FLOW_KEYS: tuple[str, ...] = (
    "upload",
    "overview",
    "mapping",
    "suggestions",
    "history",
    "export",
)

# Danh sách các mục trên menu ngang Hàng 2 của Header wireframe:
# Trang chủ · Dự án · Làm sạch dữ liệu · Thư viện quy tắc · Nhật ký · Tài khoản · Quản trị (Admin)
HEADER_NAV_KEYS: tuple[str, ...] = (
    "home",
    "dashboard",
    "suggestions",
    "rule_library",
    "audit",
    "account",
)

_BY_KEY = {page.key: page for page in PAGES}


def get_page(key: str) -> PageDef:
    """Lấy khai báo trang theo key."""
    return _BY_KEY[key]


def get_page_key(title: str | None) -> str:
    """Suy ra key trang từ tiêu đề hiển thị khi trang chưa truyền key tường minh."""
    if title == "Dashboard" or (title and title.startswith("Xin chào")):
        return "dashboard" if title == "Dashboard" else "home"
    return next((page.key for page in PAGES if page.title == title), "home")


def build_pages(logged_in: bool, admin: bool) -> list[st.Page] | dict[str, list[st.Page]]:
    """Dựng danh sách st.Page cho st.navigation theo trạng thái đăng nhập và quyền."""
    if not logged_in:
        return [_to_st_page(page, default=page.key == "login") for page in PAGES]

    sections: dict[str, list[st.Page]] = {}
    for page in PAGES:
        if page.key == "login" or (page.admin_only and not admin):
            continue
        sections.setdefault(page.group or "", []).append(_to_st_page(page))
    return sections


def _to_st_page(page: PageDef, *, default: bool | None = None) -> st.Page:
    return st.Page(
        page.file,
        title=page.title,
        icon=f":material/{page.icon}:",
        url_path=page.url_path or None,
        default=page.default if default is None else default,
    )
