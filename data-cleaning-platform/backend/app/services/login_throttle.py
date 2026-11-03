"""Chặn dò mật khẩu: sai quá nhiều lần trong một khoảng thời gian thì tạm khóa đăng nhập.

Dựa trên bảng audit_logs nên bền qua khởi động lại và dùng chung giữa nhiều tiến trình:
- mỗi lần sai ghi một dòng `auth.login_failed` (new_value.email, ip_address);
- đăng nhập đúng ghi `auth.login`, và chỉ tính các lần sai SAU lần đăng nhập đúng gần nhất;
- giới hạn theo cặp (email, IP): LOGIN_MAX_ATTEMPTS lần / LOGIN_WINDOW_MINUTES phút;
- thêm trần theo IP (LOGIN_MAX_ATTEMPTS_PER_IP) để không dò được bằng cách đổi liên tục email.
Khi đang bị chặn, yêu cầu bị từ chối TRƯỚC khi kiểm tra mật khẩu và không ghi thêm dòng nào.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.models.audit_log import AuditLog
from app.services.audit import log_action

FAILED = "auth.login_failed"
SUCCEEDED = "auth.login"
MAX_EMAIL_LENGTH = 255
LOCKED_MESSAGE = "Bạn đã thử đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {minutes} phút."


def normalize_email(email: str) -> str:
    return email.strip().lower()[:MAX_EMAIL_LENGTH]


def _window_start() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)


def _count_failures(db: Session, email: str, ip: str | None) -> int:
    since = _window_start()
    last_success = db.scalar(
        select(func.max(AuditLog.created_at)).where(
            AuditLog.action == SUCCEEDED, AuditLog.new_value["email"].astext == email
        )
    )
    if last_success is not None:
        since = max(since, last_success)
    return (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == FAILED,
                AuditLog.created_at > since,
                AuditLog.new_value["email"].astext == email,
                AuditLog.ip_address.is_(ip) if ip is None else AuditLog.ip_address == ip,
            )
        )
        or 0
    )


def _count_ip_failures(db: Session, ip: str | None) -> int:
    if ip is None:
        return 0
    return (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action == FAILED,
                AuditLog.created_at > _window_start(),
                AuditLog.ip_address == ip,
            )
        )
        or 0
    )


def ensure_not_locked(db: Session, email: str, ip: str | None) -> None:
    """Ném RateLimitError (429) nếu cặp (email, IP) hoặc IP đã sai quá số lần cho phép."""
    key = normalize_email(email)
    if (
        _count_failures(db, key, ip) >= settings.LOGIN_MAX_ATTEMPTS
        or _count_ip_failures(db, ip) >= settings.LOGIN_MAX_ATTEMPTS_PER_IP
    ):
        raise RateLimitError(LOCKED_MESSAGE.format(minutes=settings.LOGIN_WINDOW_MINUTES))


def record_failure(
    db: Session, email: str, ip: str | None, reason: str, user_id: int | None = None
) -> None:
    """Ghi một lần đăng nhập sai (không bao giờ ghi mật khẩu)."""
    log_action(
        db,
        user_id,
        FAILED,
        "user",
        user_id,
        new_value={"email": normalize_email(email), "reason": reason},
        ip_address=ip,
    )


def record_success(db: Session, email: str, ip: str | None, user_id: int) -> None:
    """Ghi đăng nhập thành công; đồng thời đặt lại bộ đếm sai của email này."""
    log_action(
        db,
        user_id,
        SUCCEEDED,
        "user",
        user_id,
        new_value={"email": normalize_email(email)},
        ip_address=ip,
    )
