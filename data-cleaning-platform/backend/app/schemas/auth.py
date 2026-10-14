"""Schema cho đăng ký, đăng nhập, đổi mật khẩu và trả JWT token."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Dữ liệu đăng ký tài khoản mới. Luôn tạo với role 'user'."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Dữ liệu đăng nhập."""

    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    """Dữ liệu đổi mật khẩu của chính user đang đăng nhập."""

    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Phản hồi chứa JWT access token sau khi đăng nhập/đăng ký thành công."""

    access_token: str
    token_type: str = "bearer"
