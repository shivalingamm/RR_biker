"""Motorcycle catalogue, AI, and 3D asset schemas."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class SpecificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    engine_cc: Optional[int] = None
    max_power_ps: Optional[Decimal] = None
    max_power_rpm: Optional[int] = None
    max_torque_nm: Optional[Decimal] = None
    max_torque_rpm: Optional[int] = None
    transmission: Optional[str] = None
    seat_height_mm: Optional[int] = None
    kerb_weight_kg: Optional[int] = None
    mileage_kmpl: Optional[Decimal] = None
    mileage_context: Optional[str] = None
    colours: Optional[str] = None


class Asset3DOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_url: str
    format: str
    fallback_image_url: Optional[str] = None
    licence: Optional[str] = None
    attribution: Optional[str] = None
    is_demonstration: bool = True


class CatalogueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manufacturer: str
    model: str
    variant: Optional[str] = None
    model_year: Optional[int] = None
    category: Optional[str] = None
    fuel_type: str
    ex_showroom_price: Optional[Decimal] = None
    currency: str = "INR"
    image_url: Optional[str] = None
    official_url: Optional[str] = None
    is_verified: bool = False
    is_demonstration: bool = True
    spec_source: Optional[str] = None
    last_verified_date: Optional[date] = None
    specification: Optional[SpecificationOut] = None
    assets_3d: list[Asset3DOut] = Field(default_factory=list)


class CompareRequest(BaseModel):
    catalogue_ids: list[int] = Field(min_length=2, max_length=4)


class AIQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
    sort: str = Field(default="relevance", pattern="^(relevance|price_asc|price_desc)$")


class AIFilters(BaseModel):
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    fuel_type: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    min_cc: Optional[int] = None
    max_cc: Optional[int] = None
    keywords: list[str] = Field(default_factory=list)


class AIQueryResponse(BaseModel):
    ai_provided: bool
    mode: str
    note: Optional[str] = None
    filters: AIFilters
    results: list[CatalogueOut]
    total: int
    page: int
    page_size: int
    pages: int


class AssistantMessage(BaseModel):
    role: str
    content: str


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[AssistantMessage] = Field(default_factory=list)
    motorcycle_id: Optional[int] = None


class AssistantResponse(BaseModel):
    ai_provided: bool
    mode: str
    note: Optional[str] = None
    answer: str
    suggestions: list[str] = Field(default_factory=list)
    data: Optional[dict[str, Any]] = None
