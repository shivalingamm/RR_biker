"""Product catalogue routes."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.core.errors import NotFoundError
from app.models import (
    Motorcycle,
    MotorcycleProductCompatibility,
    Product,
    ProductCategory,
    User,
)
from app.schemas.common import Page
from app.schemas.shop import (
    CategoryOut,
    CompatibleProductsResponse,
    CompatibilityOut,
    ProductDetailOut,
    ProductOut,
)
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> list[ProductCategory]:
    return list(db.execute(select(ProductCategory).order_by(ProductCategory.name)).scalars().all())


@router.get("", response_model=Page[ProductOut])
def list_products(
    q: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    in_stock: bool | None = None,
    sort: str = Query(default="relevance", pattern="^(relevance|price_asc|price_desc|rating)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> Page[ProductOut]:
    rows, total = product_service.search(
        db, q=q, category_slug=category, brand=brand,
        min_price=min_price, max_price=max_price, in_stock=in_stock,
        sort=sort, page=page, page_size=page_size,
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return Page[ProductOut](
        items=[product_service.serialize_product(p) for p in rows],
        total=total, page=page, page_size=page_size, pages=pages,
    )


@router.get("/compatible", response_model=CompatibleProductsResponse)
def compatible_products(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompatibleProductsResponse:
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
    label = f"{moto.manufacturer} {moto.model}" + (f" {moto.variant}" if moto.variant else "")

    if not rows:
        return CompatibleProductsResponse(
            motorcycle_id=moto.id,
            bike_label=label,
            match_confidence="unknown",
            warning=(
                "We have no verified compatibility records for this motorcycle. "
                "Products shown elsewhere are not confirmed to fit — please verify "
                "with the seller or manufacturer before purchasing."
            ),
            products=[],
        )

    return CompatibleProductsResponse(
        motorcycle_id=moto.id,
        bike_label=label,
        match_confidence="explicit",
        warning=None,
        products=[product_service.serialize_product(p) for p in rows],
    )


@router.get("/{product_id}", response_model=ProductDetailOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetailOut:
    product = product_service.get(db, product_id)
    if product is None:
        raise NotFoundError("Product not found")
    base = product_service.serialize_product(product)
    return ProductDetailOut(
        **base.model_dump(),
        compatibility=[CompatibilityOut.model_validate(c) for c in product.compatibility],
    )
