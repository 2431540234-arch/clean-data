"""API xác thực: đăng ký, đăng nhập, lấy thông tin bản thân, đổi mật khẩu."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories import user_repo
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Đăng ký tài khoản mới. Luôn tạo với role 'user' (không cho tự đăng ký admin)."""
    existing = user_repo.get_by_email(db, payload.email)
    if existing is not None:
        raise ConflictError("Email đã được sử dụng.")

    user = user_repo.create_user(
        db,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="user",
    )
    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Đăng nhập bằng email + mật khẩu, trả về JWT access token."""
    user = user_repo.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Email hoặc mật khẩu không đúng.")
    if not user.is_active:
        raise UnauthorizedError("Tài khoản đã bị khóa.")

    token = create_access_token(subject=str(user.id), extra_claims={"role": user.role})
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Trả về thông tin của user đang đăng nhập."""
    return current_user


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Đổi mật khẩu của chính user đang đăng nhập.

    Gợi ý cách làm: verify_password(payload.old_password, current_user.password_hash),
    nếu đúng thì set current_user.password_hash = hash_password(payload.new_password)
    và commit; nếu sai raise UnauthorizedError("Mật khẩu cũ không đúng.").
    """
    raise NotImplementedError("TODO: kiểm tra mật khẩu cũ và cập nhật mật khẩu mới.")
