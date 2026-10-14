"""Find My Mechanic routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import ConflictError, NotFoundError
from app.models import MechanicReview, MechanicShop, User
from app.schemas.common import Page
from app.schemas.mechanic import MechanicOut, MechanicReviewCreate, MechanicReviewOut
from app.services import mechanics as mechanic_service

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


@router.get("", response_model=Page[MechanicOut])
def search_mechanics(
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    locality: str | None = None,
    city: str | None = None,
    service: str | None = None,
    max_distance_km: float | None = Query(default=None, gt=0, le=500),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page[MechanicOut]:
    rows, total = mechanic_service.search(
        db, lat=lat, lon=lon, locality=locality, city=city, service=service,
        max_distance_km=max_distance_km, page=page, page_size=page_size,
    )
    items = [MechanicOut(**mechanic_service.serialize(r["shop"], r["distance_km"])) for r in rows]
    pages = max(1, (total + page_size - 1) // page_size)
    return Page[MechanicOut](
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/{shop_id}", response_model=MechanicOut)
def get_mechanic(
    shop_id: int,
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
    db: Session = Depends(get_db),
) -> MechanicOut:
    shop = db.execute(
        select(MechanicShop).where(MechanicShop.id == shop_id).options(selectinload(MechanicShop.services))
    ).scalar_one_or_none()
    if shop is None:
        raise NotFoundError("Mechanic not found")
    distance = None
    if lat is not None and lon is not None:
        from app.services.geo import haversine_km

        distance = haversine_km(lat, lon, shop.latitude, shop.longitude)
    return MechanicOut(**mechanic_service.serialize(shop, distance))


@router.get("/{shop_id}/reviews", response_model=list[MechanicReviewOut])
def list_reviews(shop_id: int, db: Session = Depends(get_db)) -> list[MechanicReview]:
    shop = db.get(MechanicShop, shop_id)
    if shop is None:
        raise NotFoundError("Mechanic not found")
    rows = db.execute(
        select(MechanicReview)
        .where(MechanicReview.shop_id == shop_id)
        .order_by(MechanicReview.created_at.desc())
    ).scalars().all()
    return list(rows)


@router.post("/{shop_id}/reviews", response_model=MechanicReviewOut, status_code=201)
def create_review(
    shop_id: int,
    payload: MechanicReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MechanicReview:
    shop = db.get(MechanicShop, shop_id)
    if shop is None:
        raise NotFoundError("Mechanic not found")
    existing = db.execute(
        select(MechanicReview).where(
            MechanicReview.shop_id == shop_id, MechanicReview.user_id == user.id
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictError("You have already reviewed this workshop")

    review = MechanicReview(
        shop_id=shop_id, user_id=user.id,
        rating=payload.rating, review_text=payload.review_text,
    )
    db.add(review)
    db.flush()
    _recompute_rating(db, shop)
    db.commit()
    db.refresh(review)
    return review


@router.post("/{shop_id}/reviews/{review_id}/report", response_model=MechanicReviewOut)
def report_review(
    shop_id: int,
    review_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MechanicReview:
    review = db.execute(
        select(MechanicReview).where(
            MechanicReview.id == review_id, MechanicReview.shop_id == shop_id
        )
    ).scalar_one_or_none()
    if review is None:
        raise NotFoundError("Review not found")
    review.report_count += 1
    db.commit()
    db.refresh(review)
    return review


def _recompute_rating(db: Session, shop: MechanicShop) -> None:
    avg, count = db.execute(
        select(func.avg(MechanicReview.rating), func.count(MechanicReview.id)).where(
            MechanicReview.shop_id == shop.id
        )
    ).one()
    shop.rating_avg = float(avg) if avg is not None else None
    shop.rating_count = int(count or 0)
