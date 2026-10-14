"""Dependency dùng chung cho FastAPI: lấy DB session, user hiện tại, kiểm tra quyền admin."""

from collections.abc import Generator

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Cung cấp một DB session cho mỗi request, tự đóng lại khi request kết thúc."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Giải mã JWT từ header Authorization và trả về user hiện tại.

    Raises:
        UnauthorizedError: thiếu token, token không hợp lệ/hết hạn, hoặc user
            không còn tồn tại / đã bị khóa.
    """
    if credentials is None:
        raise UnauthorizedError("Thiếu token xác thực.")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Token không hợp lệ hoặc đã hết hạn.") from exc

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id is not None else None
    if user is None:
        raise UnauthorizedError("Người dùng không tồn tại.")
    if not user.is_active:
        raise UnauthorizedError("Tài khoản đã bị khóa.")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Chỉ cho phép user có role 'admin' đi tiếp, ngược lại trả lỗi 403."""
    if current_user.role != "admin":
        raise ForbiddenError("Chỉ quản trị viên mới có quyền thực hiện hành động này.")
    return current_user
