"""Lỗi tùy chỉnh của hệ thống và exception handler trả thông báo tiếng Việt cho client."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Lỗi nghiệp vụ chung, trả về cho client kèm mã HTTP và thông báo tiếng Việt."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Không tìm thấy tài nguyên (project, dataset, version...)."""

    def __init__(self, message: str = "Không tìm thấy tài nguyên.") -> None:
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)


class ForbiddenError(AppError):
    """Người dùng không có quyền truy cập tài nguyên này."""

    def __init__(self, message: str = "Bạn không có quyền truy cập tài nguyên này.") -> None:
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


class UnauthorizedError(AppError):
    """Chưa đăng nhập hoặc token không hợp lệ."""

    def __init__(self, message: str = "Yêu cầu đăng nhập.") -> None:
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)


class ConflictError(AppError):
    """Dữ liệu bị xung đột, ví dụ email đã tồn tại."""

    def __init__(self, message: str = "Dữ liệu bị xung đột.") -> None:
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)


class ValidationAppError(AppError):
    """Dữ liệu đầu vào không hợp lệ theo nghiệp vụ (khác với lỗi Pydantic)."""

    def __init__(self, message: str = "Dữ liệu không hợp lệ.") -> None:
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


def register_exception_handlers(app: FastAPI) -> None:
    """Đăng ký exception handler cho FastAPI app, chuyển AppError thành JSONResponse."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
