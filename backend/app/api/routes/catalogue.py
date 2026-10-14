"""Verified motorcycle catalogue routes (structured search, compare, assets)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import NotFoundError
from app.models import MotorcycleCatalogue
from app.schemas.catalogue import (
    Asset3DOut,
    CatalogueOut,
    CompareRequest,
    SpecificationOut,
)
from app.schemas.common import Page
from app.services import catalogue as catalogue_service
from app.services.ai import BikeSearchFilters

router = APIRouter(prefix="/catalogue", tags=["catalogue"])


@router.get("/manufacturers", response_model=list[str])
def list_manufacturers(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(
        select(MotorcycleCatalogue.manufacturer).distinct().order_by(MotorcycleCatalogue.manufacturer)
    ).scalars().all()
    return list(rows)


@router.get("", response_model=Page[CatalogueOut])
def search_catalogue(
    manufacturer: str | None = None,
    model: str | None = None,
    category: str | None = None,
    fuel_type: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    min_cc: int | None = Query(default=None, ge=25, le=3000),
    max_cc: int | None = Query(default=None, ge=25, le=3000),
    sort: str = Query(default="relevance", pattern="^(relevance|price_asc|price_desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page[CatalogueOut]:
    filters = BikeSearchFilters(
        manufacturer=manufacturer,
        model=model,
        category=category,
        fuel_type=fuel_type,
        min_price=int(min_price) if min_price is not None else None,
        max_price=int(max_price) if max_price is not None else None,
        min_cc=min_cc,
        max_cc=max_cc,
    )
    rows, total = catalogue_service.search(db, filters, page=page, page_size=page_size, sort=sort)
    pages = max(1, (total + page_size - 1) // page_size)
    return Page[CatalogueOut](
        items=[CatalogueOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size, pages=pages,
    )


@router.post("/compare", response_model=list[CatalogueOut])
def compare_models(payload: CompareRequest, db: Session = Depends(get_db)) -> list[CatalogueOut]:
    result = []
    for cid in payload.catalogue_ids:
        row = catalogue_service.get(db, cid)
        if row:
            result.append(CatalogueOut.model_validate(row))
    if not result:
        raise NotFoundError("None of the requested models were found")
    return result


@router.get("/{catalogue_id}", response_model=CatalogueOut)
def get_catalogue_entry(catalogue_id: int, db: Session = Depends(get_db)) -> CatalogueOut:
    row = catalogue_service.get(db, catalogue_id)
    if row is None:
        raise NotFoundError("Motorcycle not found in catalogue")
    return CatalogueOut.model_validate(row)


@router.get("/{catalogue_id}/assets", response_model=list[Asset3DOut])
def get_assets(catalogue_id: int, db: Session = Depends(get_db)) -> list[Asset3DOut]:
    row = catalogue_service.get(db, catalogue_id)
    if row is None:
        raise NotFoundError("Motorcycle not found in catalogue")
    return [Asset3DOut.model_validate(a) for a in row.assets_3d]
