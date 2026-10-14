"""Mechanic discovery schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MechanicServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    estimated_price: Optional[float] = None


class MechanicOut(BaseModel):
    id: int
    name: str
    address: str
    locality: Optional[str] = None
    city: str
    latitude: float
    longitude: float
    phone: Optional[str] = None
    opening_hours: Optional[str] = None
    brands_serviced: list[str] = Field(default_factory=list)
    is_verified: bool = False
    is_demonstration: bool = True
    rating_avg: Optional[float] = None
    rating_count: int = 0
    distance_km: Optional[float] = None
    distance_label: Optional[str] = None
    services: list[MechanicServiceOut] = Field(default_factory=list)


class MechanicReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    user_id: int
    rating: int
    review_text: Optional[str] = None
    is_verified_service: bool = False
    created_at: datetime


class MechanicReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = Field(default=None, max_length=2000)
