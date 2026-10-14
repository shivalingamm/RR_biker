"""Product query + serialisation helpers."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Product, ProductCategory, Seller
from app.schemas.shop import CategoryOut, ProductImageOut, ProductOut


def serialize_product(p: Product) -> ProductOut:
    return ProductOut(
        id=p.id,
        name=p.name,
        slug=p.slug,
        description=p.description,
        brand=p.brand,
        category_id=p.category_id,
        category=CategoryOut.model_validate(p.category) if p.category else None,
        price=p.price,
        discount_percent=p.discount_percent,
        final_price=p.final_price,
        stock_qty=p.stock_qty,
        warranty_months=p.warranty_months,
        compatibility_notes=p.compatibility_notes,
        rating_avg=p.rating_avg,
        rating_count=p.rating_count,
        is_demonstration=p.is_demonstration,
        images=[ProductImageOut.model_validate(i) for i in sorted(p.images, key=lambda x: x.sort_order)],
        seller_name=p.seller.name if p.seller else None,
        seller_verified=p.seller.is_verified if p.seller else False,
    )


def _base() -> Select:
    return select(Product).options(
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.seller),
    )


def search(
    db: Session,
    *,
    q: str | None = None,
    category_slug: str | None = None,
    brand: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    stmt = _base()
    count_stmt = select(func.count(Product.id))

    def _apply(s: Select) -> Select:
        if category_slug:
            s = s.join(ProductCategory, ProductCategory.id == Product.category_id).where(
                ProductCategory.slug == category_slug
            )
        if brand:
            s = s.where(func.lower(Product.brand) == brand.lower())
        if min_price is not None:
            s = s.where(Product.price >= min_price)
        if max_price is not None:
            s = s.where(Product.price <= max_price)
        if in_stock:
            s = s.where(Product.stock_qty > 0)
        if q:
            like = f"%{q.lower()}%"
            s = s.where(
                or_(
                    func.lower(Product.name).like(like),
                    func.lower(Product.brand).like(like),
                    func.lower(Product.description).like(like),
                )
            )
        return s

    stmt = _apply(stmt)
    total = db.execute(_apply(count_stmt)).scalar_one()

    if sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc())
    elif sort == "rating":
        stmt = stmt.order_by(Product.rating_avg.desc().nulls_last())
    else:
        stmt = stmt.order_by(Product.id.desc())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return list(rows), total


def get(db: Session, product_id: int) -> Product | None:
    return db.execute(_base().where(Product.id == product_id)).scalar_one_or_none()


def get_or_create_seller(db: Session, name: str, city: str | None, verified: bool) -> Seller:
    seller = db.execute(select(Seller).where(Seller.name == name)).scalar_one_or_none()
    if seller:
        return seller
    seller = Seller(name=name, city=city, is_verified=verified, is_demonstration=True)
    db.add(seller)
    db.flush()
    return seller
