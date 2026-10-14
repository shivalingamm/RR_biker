"""Motorcycle ownership models: bikes, documents, maintenance, reminders."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

FUEL_TYPES = ("petrol", "diesel", "electric", "cng", "hybrid")

DOCUMENT_TYPES = (
    "driving_licence",
    "registration_certificate",
    "insurance",
    "puc",
    "other",
)


class Motorcycle(Base, TimestampMixin):
    __tablename__ = "motorcycles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    manufacturer: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[Optional[str]] = mapped_column(String(120))
    model_year: Mapped[Optional[int]] = mapped_column(Integer)
    registration_number: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    fuel_type: Mapped[str] = mapped_column(String(20), default="petrol", nullable=False)
    engine_cc: Mapped[Optional[int]] = mapped_column(Integer)
    odometer_km: Mapped[Optional[int]] = mapped_column(Integer)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date)
    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)

    user: Mapped["User"] = relationship(back_populates="motorcycles")
    documents: Mapped[list["MotorcycleDocument"]] = relationship(
        back_populates="motorcycle", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="motorcycle", cascade="all, delete-orphan"
    )
    reminders: Mapped[list["Reminder"]] = relationship(
        back_populates="motorcycle", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_motorcycle_user_primary", "user_id", "is_primary"),)


class MotorcycleDocument(Base, TimestampMixin):
    __tablename__ = "motorcycle_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    motorcycle_id: Mapped[int] = mapped_column(
        ForeignKey("motorcycles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    issued_date: Mapped[Optional[date]] = mapped_column(Date)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    # Never store files in a public directory; storage_key is private.
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    motorcycle: Mapped[Motorcycle] = relationship(back_populates="documents")


class MaintenanceRecord(Base, TimestampMixin):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    motorcycle_id: Mapped[int] = mapped_column(
        ForeignKey("motorcycles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    service_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    odometer_km: Mapped[Optional[int]] = mapped_column(Integer)
    service_type: Mapped[str] = mapped_column(String(80), nullable=False)
    work_performed: Mapped[Optional[str]] = mapped_column(Text)
    parts_replaced: Mapped[Optional[str]] = mapped_column(Text)
    cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    mechanic: Mapped[Optional[str]] = mapped_column(String(160))
    next_service_date: Mapped[Optional[date]] = mapped_column(Date)
    next_service_odometer_km: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    motorcycle: Mapped[Motorcycle] = relationship(back_populates="maintenance_records")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    motorcycle_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("motorcycles.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), default="maintenance", nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    due_odometer_km: Mapped[Optional[int]] = mapped_column(Integer)
    is_done: Mapped[bool] = mapped_column(default=False, nullable=False)
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    motorcycle: Mapped[Optional[Motorcycle]] = relationship(back_populates="reminders")
