"""Điểm vào backend FastAPI: khởi tạo app, cấu hình CORS, include router, endpoint health check."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings, validate_runtime_config
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.services import upload_sessions

setup_logging()

validate_runtime_config(settings)  # chặn khởi động production với cấu hình không an toàn


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Khi khởi động: dọn các phiên tải lên theo từng phần đã quá hạn (do lần chạy trước bỏ dở)."""
    try:
        upload_sessions.purge_expired()
    except Exception:  # noqa: BLE001 - dọn dẹp lỗi không được chặn ứng dụng khởi động
        logging.getLogger(__name__).warning("Không dọn được phiên tải lên quá hạn", exc_info=True)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(api_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Endpoint kiểm tra tình trạng backend, dùng cho Docker healthcheck / CI."""
    return {"status": "ok"}
