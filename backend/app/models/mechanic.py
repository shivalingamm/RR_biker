"""Mechanic discovery models."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class MechanicShop(Base, TimestampMixin):
    __tablename__ = "mechanic_shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    address: Mapped[str] = mapped_column(String(400), nullable=False)
    locality: Mapped[Optional[str]] = mapped_column(String(160), index=True)
    city: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    opening_hours: Mapped[Optional[str]] = mapped_column(String(200))
    brands_serviced: Mapped[Optional[str]] = mapped_column(String(400))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Demonstration records are clearly labelled and never presented as live.
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rating_avg: Mapped[Optional[float]] = mapped_column(Float)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    services: Mapped[list["MechanicService"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["MechanicReview"]] = relationship(
        back_populates="shop", cascade="all, delete-orphan"
    )


class MechanicService(Base, TimestampMixin):
    __tablename__ = "mechanic_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("mechanic_shops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    estimated_price: Mapped[Optional[float]] = mapped_column(Float)

    shop: Mapped[MechanicShop] = relationship(back_populates="services")


class MechanicReview(Base, TimestampMixin):
    __tablename__ = "mechanic_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("mechanic_shops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review_text: Mapped[Optional[str]] = mapped_column(Text)
    is_verified_service: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    shop: Mapped[MechanicShop] = relationship(back_populates="reviews")

    __table_args__ = (
        # one review per user per shop prevents duplicate flooding
        UniqueConstraint("shop_id", "user_id", name="uq_review_shop_user"),
    )


class MechanicBooking(Base, TimestampMixin):
    """Reserved for a future appointment workflow.

    No booking endpoints are exposed yet; the table exists so the schema does
    not need a destructive migration when the feature lands.
    """

    __tablename__ = "mechanic_bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(
        ForeignKey("mechanic_shops.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    motorcycle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("motorcycles.id", ondelete="SET NULL")
    )
    service_name: Mapped[Optional[str]] = mapped_column(String(160))
    scheduled_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="requested", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
