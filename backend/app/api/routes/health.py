"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "version": "0.1.0",
    }


@router.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {
        "status": "ready",
        "database": "ok",
        "integrations": {
            "ai": "configured" if settings.is_ai_configured else "fallback",
            "maps": "configured" if settings.is_maps_configured else "fallback",
        },
    }
