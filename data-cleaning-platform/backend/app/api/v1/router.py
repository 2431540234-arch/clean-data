"""Gom toàn bộ router của API v1 thành một router duy nhất để main.py include."""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    audit,
    auth,
    datasets,
    export,
    mapping,
    preview,
    profiling,
    projects,
    quality,
    rules,
    suggestions,
    versions,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(projects.router)
api_router.include_router(datasets.router)
api_router.include_router(profiling.router)
api_router.include_router(suggestions.router)
api_router.include_router(mapping.router)
api_router.include_router(preview.router)
api_router.include_router(versions.router)
api_router.include_router(rules.router)
api_router.include_router(quality.router)
api_router.include_router(export.router)
api_router.include_router(audit.router)
