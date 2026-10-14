"""Điểm vào backend FastAPI: khởi tạo app, cấu hình CORS, include router, endpoint health check."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(title=settings.APP_NAME)

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
