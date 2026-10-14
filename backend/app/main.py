"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.errors import register_exception_handlers

# Import models so metadata is registered before create_all.
import app.models  # noqa: F401

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="BIKER — motorcycle ownership, accessories, AI studio and mechanic discovery.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
def on_startup() -> None:
    # Convenience for local development / SQLite. In production, run Alembic.
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "app": settings.app_name,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
        "health": f"{settings.api_prefix}/health",
    }
