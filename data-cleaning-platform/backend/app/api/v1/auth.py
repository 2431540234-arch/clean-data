"""API xác thực: đăng ký, đăng nhập, lấy thông tin bản thân, đổi mật khẩu."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.request_info import client_ip
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories import user_repo
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services import login_throttle
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])

WRONG_CREDENTIALS = "Email hoặc mật khẩu không đúng."


def _token_for(user: User) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"role": user.role})


@router.post("/register", response_model=TokenResponse)
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    """Đăng ký tài khoản mới. Luôn tạo với role 'user' (không cho tự đăng ký admin)."""
    email = payload.email.strip().lower()
    if user_repo.get_by_email(db, email) is not None:
        raise ConflictError("Email đã được sử dụng.")

    user = user_repo.create_user(
        db,
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="user",
    )
    log_action(
        db,
        user.id,
        "auth.register",
        "user",
        user.id,
        new_value={"email": user.email},
        ip_address=client_ip(request),
    )
    return TokenResponse(access_token=_token_for(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    """Đăng nhập bằng email + mật khẩu, trả về JWT access token.

    Sai quá LOGIN_MAX_ATTEMPTS lần trong LOGIN_WINDOW_MINUTES phút (theo email + IP) thì bị chặn
    với mã 429. Mỗi lần đăng nhập (đúng/sai) được ghi nhật ký, không bao giờ kèm mật khẩu.
    """
    ip = client_ip(request)
    login_throttle.ensure_not_locked(db, payload.email, ip)

    user = user_repo.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        login_throttle.record_failure(
            db,
            payload.email,
            ip,
            "unknown_email" if user is None else "wrong_password",
            user and user.id,
        )
        raise UnauthorizedError(WRONG_CREDENTIALS)
    if not user.is_active:
        login_throttle.record_failure(db, payload.email, ip, "locked", user.id)
        raise UnauthorizedError("Tài khoản đã bị khóa.")

    login_throttle.record_success(db, payload.email, ip, user.id)
    return TokenResponse(access_token=_token_for(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Trả về thông tin của user đang đăng nhập."""
    return current_user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Đổi mật khẩu của chính user đang đăng nhập.

    Mọi token cũ (kể cả token đang dùng) bị vô hiệu; phản hồi kèm `access_token` mới cho phiên
    hiện tại. Sai mật khẩu cũ quá nhiều lần cũng bị chặn như đăng nhập sai.
    """
    ip = client_ip(request)
    login_throttle.ensure_not_locked(db, f"change:{current_user.id}", ip)
    if not verify_password(payload.old_password, current_user.password_hash):
        login_throttle.record_failure(
            db, f"change:{current_user.id}", ip, "wrong_old_password", current_user.id
        )
        raise UnauthorizedError("Mật khẩu cũ không đúng.")
    if payload.new_password == payload.old_password:
        raise ValidationAppError("Mật khẩu mới phải khác mật khẩu hiện tại.")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(UTC)
    log_action(
        db,
        current_user.id,
        "auth.change_password",
        "user",
        current_user.id,
        ip_address=ip,
        commit=False,
    )
    db.commit()
    return {
        "message": "Đã đổi mật khẩu.",
        "access_token": _token_for(current_user),
        "token_type": "bearer",
    }
