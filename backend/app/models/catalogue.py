"""Verified motorcycle catalogue, specifications, and 3D asset registry."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class MotorcycleCatalogue(Base, TimestampMixin):
    __tablename__ = "motorcycle_catalogue"

    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    model: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    variant: Mapped[Optional[str]] = mapped_column(String(120))
    model_year: Mapped[Optional[int]] = mapped_column(Integer)
    category: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    fuel_type: Mapped[str] = mapped_column(String(20), default="petrol", nullable=False)
    ex_showroom_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    official_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Provenance: never invent specs. Unverified rows must be labelled.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    spec_source: Mapped[Optional[str]] = mapped_column(String(300))
    last_verified_date: Mapped[Optional[date]] = mapped_column(Date)

    specification: Mapped[Optional["MotorcycleSpecification"]] = relationship(
        back_populates="catalogue", uselist=False, cascade="all, delete-orphan"
    )
    assets_3d: Mapped[list["Motorcycle3DAsset"]] = relationship(
        back_populates="catalogue", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "manufacturer", "model", "variant", "model_year",
            name="uq_catalogue_identity",
        ),
    )


class MotorcycleSpecification(Base, TimestampMixin):
    __tablename__ = "motorcycle_specifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    catalogue_id: Mapped[int] = mapped_column(
        ForeignKey("motorcycle_catalogue.id", ondelete="CASCADE"),
        unique=True, index=True, nullable=False,
    )
    engine_cc: Mapped[Optional[int]] = mapped_column(Integer)
    max_power_ps: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    max_power_rpm: Mapped[Optional[int]] = mapped_column(Integer)
    max_torque_nm: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2))
    max_torque_rpm: Mapped[Optional[int]] = mapped_column(Integer)
    transmission: Mapped[Optional[str]] = mapped_column(String(120))
    seat_height_mm: Mapped[Optional[int]] = mapped_column(Integer)
    kerb_weight_kg: Mapped[Optional[int]] = mapped_column(Integer)
    mileage_kmpl: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    mileage_context: Mapped[Optional[str]] = mapped_column(String(300))
    colours: Mapped[Optional[str]] = mapped_column(String(400))
    extra: Mapped[Optional[str]] = mapped_column(Text)

    catalogue: Mapped[MotorcycleCatalogue] = relationship(back_populates="specification")


class Motorcycle3DAsset(Base, TimestampMixin):
    __tablename__ = "motorcycle_3d_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    catalogue_id: Mapped[int] = mapped_column(
        ForeignKey("motorcycle_catalogue.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Empty/None means no real GLB is registered; the app shows a labelled
    # fallback. Never store a fabricated asset URL.
    asset_url: Mapped[Optional[str]] = mapped_column(String(500))
    format: Mapped[str] = mapped_column(String(20), default="glb", nullable=False)
    fallback_image_url: Mapped[Optional[str]] = mapped_column(String(500))
    licence: Mapped[Optional[str]] = mapped_column(String(200))
    attribution: Mapped[Optional[str]] = mapped_column(String(300))
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    catalogue: Mapped[MotorcycleCatalogue] = relationship(back_populates="assets_3d")
