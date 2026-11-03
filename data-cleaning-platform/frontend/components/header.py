"""Header ứng dụng 2 hàng chuẩn theo Wireframe Khung 15.

Hàng 1: Logo DC DataClean, Breadcrumb vị trí trang, Selectbox chọn dự án nhanh,
        Pill thông tin người dùng (avatar, tên, vai trò) và nút Đăng xuất.
Hàng 2: Menu ngang các trang (Trang chủ, Dự án, Làm sạch dữ liệu, Thư viện quy tắc,
        Nhật ký, Tài khoản, Quản trị), đánh dấu trang đang mở.
Hỗ trợ responsive 375px: cuộn ngang hoặc flex-wrap gọn gàng, không xếp chồng thành cột dọc.
"""

from html import escape
import streamlit as st

from api_client import APIError, list_projects
from components.navigation import HEADER_NAV_KEYS, get_page
from components.ui import badge_html
from state import (
    get_context,
    get_current_user,
    get_token,
    is_admin,
    is_logged_in,
    logout,
    set_context,
    set_flash,
)


def render_header(current_page_key: str = "home") -> None:
    """Vẽ Header 2 hàng ở đầu trang."""
    if not is_logged_in():
        return

    user = get_current_user() or {}
    name = str(user.get("full_name") or user.get("email") or "Người dùng")
    initials = "".join([part[0] for part in name.split() if part])[:2].upper() or "DC"
    role_label = "Quản trị viên" if is_admin() else "Người dùng"
    role_kind = "primary" if is_admin() else "neutral"

    # Lấy thông tin trang hiện tại để làm breadcrumb
    page_def = get_page(current_page_key)
    page_title = page_def.title
    area_name = page_def.group or "Chung"

    # --- HÀNG 1: TOP BAR ---
    top_col_brand, top_col_project, top_col_user, top_col_logout = st.columns(
        [3.5, 3.5, 3.2, 1.3], gap="small", vertical_alignment="center"
    )

    with top_col_brand:
        st.markdown(
            f"""<div class="dc-header-brand">
                <span class="dc-logo-badge">DC</span>
                <span class="dc-logo-text">DataClean</span>
                <span class="dc-breadcrumb-sep">·</span>
                <span class="dc-breadcrumb-area">{escape(area_name)}</span>
                <span class="dc-breadcrumb-sep">/</span>
                <span class="dc-breadcrumb-title">{escape(page_title)}</span>
            </div>""",
            unsafe_allow_html=True,
        )

    with top_col_project:
        projects = []
        token = get_token()
        if token:
            try:
                projects = list_projects(token)
            except APIError:
                projects = []

        context = get_context()
        active_project_id = context.get("project_id")

        if projects:
            options = {p["id"]: p["name"] for p in projects}
            p_ids = list(options.keys())
            current_idx = p_ids.index(active_project_id) if active_project_id in p_ids else 0

            selected_pid = st.selectbox(
                "Dự án",
                options=p_ids,
                index=current_idx,
                format_func=lambda pid: f"📁 {options.get(pid, pid)}",
                label_visibility="collapsed",
                key="header_quick_project_select",
            )
            if selected_pid != active_project_id:
                set_context(project_id=selected_pid)
                st.rerun()
        else:
            st.caption("📁 *Chưa có dự án*")

    with top_col_user:
        badge_code = badge_html(role_label, role_kind)
        st.markdown(
            f"""<div class="dc-header-user-pill">
                <div class="dc-user-avatar">{escape(initials)}</div>
                <div class="dc-user-meta">
                    <span class="dc-user-name" title="{escape(name)}">{escape(name)}</span>
                    {badge_code}
                </div>
            </div>""",
            unsafe_allow_html=True,
        )

    with top_col_logout:
        if st.button("Đăng xuất", key="header_logout_btn", icon=":material/logout:", help="Đăng xuất khỏi hệ thống"):
            logout()
            set_flash("Bạn đã đăng xuất thành công.", "info")
            st.rerun()

    # --- HÀNG 2: MENU NGANG ĐIỀU HƯỚNG ---
    nav_keys = list(HEADER_NAV_KEYS)
    if is_admin():
        nav_keys.append("admin_users")

    nav_cols = st.columns(len(nav_keys), gap="small")

    active_nav_key = current_page_key
    if current_page_key in ("upload", "overview", "mapping", "suggestions", "history", "export"):
        active_nav_key = "suggestions"
    elif current_page_key in ("admin_users", "admin_stats"):
        active_nav_key = "admin_users"

    for col, key in zip(nav_cols, nav_keys, strict=True):
        p = get_page(key)
        nav_label = "Quản trị" if key == "admin_users" else p.title
        with col:
            # st.page_link xử lý an toàn cho cả khi chạy app.py lẫn khi chạy AppTest
            try:
                st.page_link(
                    p.file,
                    label=nav_label,
                    icon=f":material/{p.icon}:",
                    use_container_width=True,
                    help=f"Mở trang {nav_label}",
                )
            except Exception:
                try:
                    rel_file = p.file.split("/")[-1]
                    st.page_link(
                        rel_file,
                        label=nav_label,
                        icon=f":material/{p.icon}:",
                        use_container_width=True,
                        help=f"Mở trang {nav_label}",
                    )
                except Exception:
                    st.button(nav_label, icon=f":material/{p.icon}:", key=f"hdr_nav_btn_{key}", use_container_width=True)

    st.markdown('<div class="dc-header-divider"></div>', unsafe_allow_html=True)
