"""AI Bike Studio routes.

Natural-language search is converted into *validated* filters; the model never
produces SQL. Assistant answers are grounded in a catalogue context snippet.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.core.ratelimit import RateLimiter, client_key
from app.models import (
    Motorcycle,
    MotorcycleCatalogue,
    MotorcycleProductCompatibility,
    Product,
    User,
)
from app.schemas.catalogue import (
    AIFilters,
    AIQueryRequest,
    AIQueryResponse,
    AssistantRequest,
    AssistantResponse,
    CatalogueOut,
)
from app.schemas.shop import CompatibleProductsResponse, ProductOut
from app.services import ai as ai_service
from app.services import catalogue as catalogue_service
from app.services import products as product_service

router = APIRouter(prefix="/ai", tags=["ai"])

_ai_limiter = RateLimiter(max_calls=30, window_seconds=60)


@router.get("/status")
def ai_status() -> dict:
    return {
        "configured": settings.is_ai_configured,
        "model": settings.openai_model if settings.is_ai_configured else None,
        "mode": "live" if settings.is_ai_configured else "fallback",
        "note": (
            None if settings.is_ai_configured
            else "Set OPENAI_API_KEY to enable the live AI model. Deterministic fallback is active."
        ),
    }


@router.post("/search", response_model=AIQueryResponse)
def ai_search(
    payload: AIQueryRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AIQueryResponse:
    _ai_limiter.check(f"ai_search:{client_key(request)}")
    manufacturers = list(
        db.execute(select(MotorcycleCatalogue.manufacturer).distinct()).scalars().all()
    )
    result = ai_service.interpret_search_query(payload.query, known_manufacturers=manufacturers)
    filters = ai_service.BikeSearchFilters(**result.data)
    rows, total = catalogue_service.search(
        db, filters, page=payload.page, page_size=payload.page_size, sort=payload.sort
    )
    pages = max(1, (total + payload.page_size - 1) // payload.page_size)
    return AIQueryResponse(
        ai_provided=result.provided,
        mode=result.mode,
        note=result.note,
        filters=AIFilters(**filters.model_dump()),
        results=[CatalogueOut.model_validate(r) for r in rows],
        total=total, page=payload.page, page_size=payload.page_size, pages=pages,
    )


@router.post("/assistant", response_model=AssistantResponse)
def assistant(
    payload: AssistantRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantResponse:
    _ai_limiter.check(f"ai_assistant:{client_key(request)}")

    context = catalogue_service.build_assistant_context(db, payload.question)
    if payload.motorcycle_id:
        moto = db.execute(
            select(Motorcycle).where(
                Motorcycle.id == payload.motorcycle_id, Motorcycle.user_id == user.id
            )
        ).scalar_one_or_none()
        if moto:
            context += (
                f"\nUSER BIKE: {moto.manufacturer} {moto.model} {moto.variant or ''} "
                f"({moto.engine_cc or '?'}cc, {moto.fuel_type})"
            )

    result = ai_service.assistant_reply(
        question=payload.question,
        context=context,
        history=[m.model_dump() for m in payload.history],
    )
    answer = result.data.get("answer", "")
    suggestions = result.data.get("suggestions", []) or [
        "Compare two models",
        "Show bikes under ₹2,00,000",
        "Find commuting bikes 150-250cc",
    ]
    return AssistantResponse(
        ai_provided=result.provided,
        mode=result.mode,
        note=result.note,
        answer=answer,
        suggestions=suggestions,
    )


@router.get("/compatible-products", response_model=CompatibleProductsResponse)
def ai_compatible_products(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompatibleProductsResponse:
    """Compatible product suggestions using explicit compatibility records only."""
    moto = db.execute(
        select(Motorcycle).where(Motorcycle.id == motorcycle_id, Motorcycle.user_id == user.id)
    ).scalar_one_or_none()
    if moto is None:
        raise NotFoundError("Motorcycle not found")

    stmt = (
        select(Product)
        .join(MotorcycleProductCompatibility, MotorcycleProductCompatibility.product_id == Product.id)
        .where(
            func.lower(MotorcycleProductCompatibility.manufacturer) == moto.manufacturer.lower(),
            func.lower(MotorcycleProductCompatibility.model) == moto.model.lower(),
        )
        .options(selectinload(Product.images), selectinload(Product.category), selectinload(Product.seller))
    )
    rows = list(db.execute(stmt).scalars().all())
    label = f"{moto.manufacturer} {moto.model}"
    if not rows:
        return CompatibleProductsResponse(
            motorcycle_id=moto.id,
            bike_label=label,
            match_confidence="unknown",
            warning=(
                "No verified compatibility records exist for this motorcycle yet. "
                "I will not guess which accessories fit."
            ),
            products=[],
        )
    return CompatibleProductsResponse(
        motorcycle_id=moto.id,
        bike_label=label,
        match_confidence="explicit",
        warning=None,
        products=[ProductOut(**product_service.serialize_product(p).model_dump()) for p in rows],
    )
