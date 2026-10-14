"""Mechanic proximity search over stored records.

Distance is computed with the haversine formula. Results are always dataset
rows; we never synthesise locations. Demonstration rows carry an explicit flag.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import MechanicService, MechanicShop
from app.services.geo import format_distance, haversine_km


def _base(stmt):
    return stmt.options(selectinload(MechanicShop.services))


def search(
    db: Session,
    *,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    locality: Optional[str] = None,
    city: Optional[str] = None,
    service: Optional[str] = None,
    max_distance_km: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    stmt = _base(select(MechanicShop))
    if locality:
        stmt = stmt.where(func.lower(MechanicShop.locality).like(f"%{locality.lower()}%"))
    if city:
        stmt = stmt.where(func.lower(MechanicShop.city) == city.lower())
    if service:
        stmt = stmt.join(MechanicService).where(
            or_(
                func.lower(MechanicService.name).like(f"%{service.lower()}%"),
                func.lower(MechanicService.description).like(f"%{service.lower()}%"),
            )
        )
    shops = db.execute(stmt).unique().scalars().all()

    results: list[dict] = []
    for shop in shops:
        distance = None
        if lat is not None and lon is not None:
            distance = haversine_km(lat, lon, shop.latitude, shop.longitude)
            if max_distance_km is not None and distance > max_distance_km:
                continue
        results.append({"shop": shop, "distance_km": distance})

    if lat is not None and lon is not None:
        results.sort(key=lambda r: r["distance_km"])
    else:
        results.sort(key=lambda r: r["shop"].name)

    total = len(results)
    start = (page - 1) * page_size
    return results[start : start + page_size], total


def serialize(shop: MechanicShop, distance_km: Optional[float]) -> dict:
    return {
        "id": shop.id,
        "name": shop.name,
        "address": shop.address,
        "locality": shop.locality,
        "city": shop.city,
        "latitude": shop.latitude,
        "longitude": shop.longitude,
        "phone": shop.phone,
        "opening_hours": shop.opening_hours,
        "brands_serviced": [b.strip() for b in (shop.brands_serviced or "").split(",") if b.strip()],
        "is_verified": shop.is_verified,
        "is_demonstration": shop.is_demonstration,
        "rating_avg": shop.rating_avg,
        "rating_count": shop.rating_count,
        "distance_km": round(distance_km, 2) if distance_km is not None else None,
        "distance_label": format_distance(distance_km) if distance_km is not None else None,
        "services": [
            {"id": s.id, "name": s.name, "description": s.description, "estimated_price": s.estimated_price}
            for s in shop.services
        ],
    }
