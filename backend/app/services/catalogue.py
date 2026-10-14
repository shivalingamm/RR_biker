"""Motorcycle catalogue queries driven by validated filters only."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import MotorcycleCatalogue, MotorcycleSpecification
from app.services.ai import BikeSearchFilters


def _base_query() -> Select:
    return select(MotorcycleCatalogue).options(
        joinedload(MotorcycleCatalogue.specification),
        joinedload(MotorcycleCatalogue.assets_3d),
    )


def apply_filters(stmt: Select, f: BikeSearchFilters) -> Select:
    if f.manufacturer:
        stmt = stmt.where(func.lower(MotorcycleCatalogue.manufacturer) == f.manufacturer.lower())
    if f.model:
        stmt = stmt.where(func.lower(MotorcycleCatalogue.model).contains(f.model.lower()))
    if f.category:
        stmt = stmt.where(func.lower(MotorcycleCatalogue.category) == f.category.lower())
    if f.fuel_type:
        stmt = stmt.where(func.lower(MotorcycleCatalogue.fuel_type) == f.fuel_type.lower())
    if f.min_price is not None:
        stmt = stmt.where(MotorcycleCatalogue.ex_showroom_price >= f.min_price)
    if f.max_price is not None:
        stmt = stmt.where(MotorcycleCatalogue.ex_showroom_price <= f.max_price)
    if f.min_cc is not None or f.max_cc is not None:
        stmt = stmt.join(
            MotorcycleSpecification,
            MotorcycleSpecification.catalogue_id == MotorcycleCatalogue.id,
            isouter=True,
        )
        if f.min_cc is not None:
            stmt = stmt.where(MotorcycleSpecification.engine_cc >= f.min_cc)
        if f.max_cc is not None:
            stmt = stmt.where(MotorcycleSpecification.engine_cc <= f.max_cc)
    if f.keywords:
        clauses = []
        for kw in f.keywords:
            like = f"%{kw.lower()}%"
            clauses.append(func.lower(MotorcycleCatalogue.manufacturer).like(like))
            clauses.append(func.lower(MotorcycleCatalogue.model).like(like))
            clauses.append(func.lower(MotorcycleCatalogue.category).like(like))
        if clauses:
            stmt = stmt.where(or_(*clauses))
    return stmt


def search(
    db: Session,
    f: BikeSearchFilters,
    *,
    page: int = 1,
    page_size: int = 20,
    sort: str = "relevance",
) -> tuple[list[MotorcycleCatalogue], int]:
    stmt = apply_filters(_base_query(), f)
    count_stmt = apply_filters(
        select(func.count(func.distinct(MotorcycleCatalogue.id))), f
    )
    total = db.execute(count_stmt).scalar_one()

    if sort == "price_asc":
        stmt = stmt.order_by(MotorcycleCatalogue.ex_showroom_price.asc().nulls_last())
    elif sort == "price_desc":
        stmt = stmt.order_by(MotorcycleCatalogue.ex_showroom_price.desc().nulls_last())
    else:
        stmt = stmt.order_by(MotorcycleCatalogue.manufacturer, MotorcycleCatalogue.model)

    stmt = stmt.distinct().offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).unique().scalars().all()
    return list(rows), total


def get(db: Session, catalogue_id: int) -> Optional[MotorcycleCatalogue]:
    return db.execute(
        _base_query().where(MotorcycleCatalogue.id == catalogue_id)
    ).unique().scalar_one_or_none()


def build_assistant_context(db: Session, query: str, *, limit: int = 8) -> str:
    """Compact, verified catalogue context for the assistant prompt."""
    f = BikeSearchFilters(keywords=[w for w in query.lower().split() if len(w) > 3][:6])
    rows, _ = search(db, f, page=1, page_size=limit)
    if not rows:
        rows = db.execute(_base_query().limit(limit)).unique().scalars().all()
    lines = []
    for r in rows:
        spec = r.specification
        parts = [f"{r.manufacturer} {r.model}"]
        if r.variant:
            parts.append(r.variant)
        if r.ex_showroom_price is not None:
            parts.append(f"₹{int(r.ex_showroom_price):,}")
        if spec and spec.engine_cc:
            parts.append(f"{spec.engine_cc}cc")
        if spec and spec.max_power_ps is not None:
            parts.append(f"{spec.max_power_ps}PS")
        if spec and spec.mileage_kmpl is not None:
            parts.append(f"~{spec.mileage_kmpl}kmpl ({spec.mileage_context or 'claim'})")
        verified = "verified" if r.is_verified else "UNVERIFIED (do not state as fact)"
        parts.append(verified)
        lines.append("- " + ", ".join(parts))
    return "\n".join(lines) if lines else "No catalogue entries available."
