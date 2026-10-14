"""Motorcycle, document, maintenance, and reminder schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

FuelType = Literal["petrol", "diesel", "electric", "cng", "hybrid"]
DocType = Literal["driving_licence", "registration_certificate", "insurance", "puc", "other"]
ReminderCategory = Literal["insurance", "puc", "service", "maintenance", "other"]


class MotorcycleBase(BaseModel):
    manufacturer: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    variant: Optional[str] = Field(default=None, max_length=120)
    model_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    registration_number: Optional[str] = Field(default=None, max_length=20)
    fuel_type: FuelType = "petrol"
    engine_cc: Optional[int] = Field(default=None, ge=25, le=3000)
    odometer_km: Optional[int] = Field(default=None, ge=0, le=2_000_000)
    purchase_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class MotorcycleCreate(MotorcycleBase):
    pass


class MotorcycleUpdate(BaseModel):
    manufacturer: Optional[str] = Field(default=None, min_length=1, max_length=80)
    model: Optional[str] = Field(default=None, min_length=1, max_length=120)
    variant: Optional[str] = None
    model_year: Optional[int] = Field(default=None, ge=1900, le=2100)
    registration_number: Optional[str] = None
    fuel_type: Optional[FuelType] = None
    engine_cc: Optional[int] = Field(default=None, ge=25, le=3000)
    odometer_km: Optional[int] = Field(default=None, ge=0, le=2_000_000)
    purchase_date: Optional[date] = None
    notes: Optional[str] = None
    is_primary: Optional[bool] = None


class MotorcycleOut(MotorcycleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_path: Optional[str] = None
    is_primary: bool = False
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    motorcycle_id: int
    doc_type: str
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    file_name: str
    content_type: str
    size_bytes: int
    upload_status: str
    notes: Optional[str] = None
    created_at: datetime


class DocumentUpdate(BaseModel):
    doc_type: Optional[DocType] = None
    issued_date: Optional[date] = None
    expiry_date: Optional[date] = None
    notes: Optional[str] = None


class MaintenanceCreate(BaseModel):
    service_date: date
    odometer_km: Optional[int] = Field(default=None, ge=0, le=2_000_000)
    service_type: str = Field(min_length=1, max_length=80)
    work_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    cost: Optional[Decimal] = Field(default=None, ge=0, le=100_000_000)
    mechanic: Optional[str] = Field(default=None, max_length=160)
    next_service_date: Optional[date] = None
    next_service_odometer_km: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    service_date: Optional[date] = None
    odometer_km: Optional[int] = Field(default=None, ge=0)
    service_type: Optional[str] = None
    work_performed: Optional[str] = None
    parts_replaced: Optional[str] = None
    cost: Optional[Decimal] = Field(default=None, ge=0)
    mechanic: Optional[str] = None
    next_service_date: Optional[date] = None
    next_service_odometer_km: Optional[int] = None
    notes: Optional[str] = None


class MaintenanceOut(MaintenanceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    motorcycle_id: int
    created_at: datetime


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: Optional[str] = None
    category: ReminderCategory = "maintenance"
    due_date: Optional[date] = None
    due_odometer_km: Optional[int] = Field(default=None, ge=0)
    motorcycle_id: Optional[int] = None


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[ReminderCategory] = None
    due_date: Optional[date] = None
    due_odometer_km: Optional[int] = None
    is_done: Optional[bool] = None


class ReminderOut(ReminderCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_done: bool
    created_at: datetime
