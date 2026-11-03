"""Đọc cấu hình hệ thống từ biến môi trường (file .env) bằng pydantic-settings.

Mọi secret (JWT_SECRET, API key, storage key...) đều phải lấy từ biến môi trường,
không hardcode trong code.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "change-me-to-a-random-secret"


class Settings(BaseSettings):
    """Tập hợp toàn bộ cấu hình của backend."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),  # chạy từ backend/ hoặc từ gốc project
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/data_cleaning"

    # JWT / Auth
    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # AI provider. Không có khóa API thì AI tự tắt và hệ thống chỉ dùng gợi ý theo quy tắc.
    AI_PROVIDER: str = "anthropic"
    AI_MODEL: str = "claude-haiku-5-5"
    AI_TIMEOUT_SECONDS: int = 20
    AI_MAX_COLUMNS: int = 40  # số cột tối đa đưa vào tóm tắt gửi cho AI
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Storage: "local" (thư mục trên đĩa), "s3" (S3-compatible) hoặc rỗng = tự chọn:
    # có STORAGE_ENDPOINT thì dùng s3, ngược lại dùng local.
    STORAGE_BACKEND: str = ""
    STORAGE_LOCAL_DIR: str = "data/storage"
    STORAGE_ENDPOINT: str = ""
    STORAGE_BUCKET: str = "data-cleaning-platform"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""

    # Frontend / CORS
    BACKEND_URL: str = "http://localhost:8000"
    # allow_credentials=True nên KHÔNG được dùng "*": mặc định chỉ cho origin của frontend.
    CORS_ORIGINS: list[str] = ["http://localhost:8501"]
    # Chỉ bật khi backend nằm sau reverse proxy tin cậy (lấy IP thật từ X-Forwarded-For).
    TRUST_PROXY_HEADERS: bool = False

    # Upload
    MAX_UPLOAD_MB: int = 50
    MAX_UPLOAD_ROWS: int = 1_000_000
    MAX_UPLOAD_COLUMNS: int = 500

    # Chống dò mật khẩu: tối đa N lần đăng nhập sai trong cửa sổ M phút theo (email, IP)
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_WINDOW_MINUTES: int = 15
    LOGIN_MAX_ATTEMPTS_PER_IP: int = 50  # trần chung theo IP, chặn dò nhiều email khác nhau

    # App
    APP_NAME: str = "Data Cleaning Platform"
    ENVIRONMENT: str = "development"


def validate_runtime_config(current: "Settings") -> None:
    """Từ chối khởi động production với cấu hình không an toàn (gọi một lần ở app.main)."""
    if current.ENVIRONMENT.lower() != "production":
        return
    if current.JWT_SECRET == DEFAULT_JWT_SECRET:
        raise RuntimeError(
            "Production phải đặt JWT_SECRET ngẫu nhiên, không dùng giá trị mặc định."
        )
    if "*" in current.CORS_ORIGINS:
        raise RuntimeError('Production phải liệt kê CORS_ORIGINS cụ thể, không dùng "*".')


@lru_cache
def get_settings() -> Settings:
    """Trả về instance Settings duy nhất (cache lại để không đọc lại .env nhiều lần)."""
    return Settings()


settings = get_settings()
