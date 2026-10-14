"""Đọc cấu hình hệ thống từ biến môi trường (file .env) bằng pydantic-settings.

Mọi secret (JWT_SECRET, API key, storage key...) đều phải lấy từ biến môi trường,
không hardcode trong code.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    JWT_SECRET: str = "change-me-to-a-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # AI provider
    AI_PROVIDER: str = "anthropic"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Storage (S3-compatible)
    STORAGE_ENDPOINT: str = ""
    STORAGE_BUCKET: str = "data-cleaning-platform"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""

    # Frontend / CORS
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: list[str] = ["*"]

    # Upload
    MAX_UPLOAD_MB: int = 50

    # App
    APP_NAME: str = "Data Cleaning Platform"
    ENVIRONMENT: str = "development"


@lru_cache
def get_settings() -> Settings:
    """Trả về instance Settings duy nhất (cache lại để không đọc lại .env nhiều lần)."""
    return Settings()


settings = get_settings()
