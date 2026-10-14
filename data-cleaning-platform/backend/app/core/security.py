"""Băm/so khớp mật khẩu (bcrypt) và tạo/giải mã JWT access token."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Băm mật khẩu thuần bằng bcrypt."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """So khớp mật khẩu thuần với hash đã lưu."""
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Tạo JWT access token.

    Args:
        subject: định danh user (thường là user.id dạng chuỗi).
        extra_claims: các claim bổ sung, ví dụ {"role": "admin"}.
    """
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Giải mã JWT access token.

    Raises:
        jwt.PyJWTError: nếu token không hợp lệ hoặc đã hết hạn.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
