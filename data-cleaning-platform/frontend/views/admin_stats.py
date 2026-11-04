"""Trang Thống kê hệ thống: chỉ admin. Chỉ hiện các trường có trong schema GET /admin/stats."""

import streamlit as st

from api_client import admin_stats
from components.charts import render_donut_chart
from components.formatting import format_number
from components.quality_gauge import render_quality_gauge, score_label
from components.ui import (
    admin_subnav,
    badge_html,
    error_state,
    metric_card,
    page_shell,
    safe_call,
    section,
)
from state import get_token

_ACTIVE, _LOCKED, _ADMIN, _USER = "#16A34A", "#DC2626", "#2563EB", "#94A3B8"

page_shell("Thống kê hệ thống", "Theo dõi người dùng và dữ liệu toàn hệ thống", admin=True)
admin_subnav()

if st.button("Làm mới", icon=":material/refresh:"):
    st.rerun()

stats, error = safe_call("Đang tải thống kê…", admin_stats, get_token())
if error is not None:
    error_state(error, key="admin_stats")
    st.stop()

locked = stats["total_users"] - stats["active_users"]
tiles = [
    (
        "Tổng người dùng",
        format_number(stats["total_users"]),
        f"{format_number(stats['active_users'])} hoạt động · {format_number(locked)} bị khóa",
    ),
    ("Tổng dự án", format_number(stats["total_projects"]), "Của mọi người dùng"),
    ("Dataset", format_number(stats["total_datasets"]), "Đã tải lên toàn hệ thống"),
    ("Lượt gọi AI", format_number(stats["total_ai_calls"]), "Gợi ý làm sạch và mapping bằng AI"),
]
for cell, (label, value, note) in zip(st.columns(len(tiles)), tiles, strict=True):
    with cell:
        metric_card(label, value, note=note)

users_col, roles_col, quality_col = st.columns(3)
with users_col, section("Người dùng theo trạng thái"):
    render_donut_chart(
        [("Hoạt động", stats["active_users"]), ("Đã khóa", locked)], [_ACTIVE, _LOCKED]
    )
with roles_col, section("Người dùng theo quyền"):
    render_donut_chart(
        [
            ("Quản trị viên", stats["total_admins"]),
            ("Người dùng", stats["total_users"] - stats["total_admins"]),
        ],
        [_ADMIN, _USER],
    )
with quality_col, section("Điểm chất lượng trung bình"):
    score = stats["average_quality_score"]
    if score is None:
        st.caption("Chưa có dataset nào được tính điểm chất lượng.")
    else:
        render_quality_gauge(score)
        label, kind = score_label(score)
        value = f"{score:.1f}".replace(".", ",")
        st.markdown(f"**{value} / 100** {badge_html(label, kind)}", unsafe_allow_html=True)
