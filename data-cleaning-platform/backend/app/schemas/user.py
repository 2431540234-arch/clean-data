"""Schema thông tin user trả về cho client và cập nhật user bởi admin."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserOut(BaseModel):
    """Thông tin user trả về cho client (không bao giờ trả password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdateByAdmin(BaseModel):
    """Admin cập nhật role / trạng thái khóa của một user."""

    role: str | None = None
    is_active: bool | None = None
