"""Shopping schemas."""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_PINCODE = re.compile(r"^[1-9][0-9]{5}$")


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: Optional[str] = None


class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    alt_text: Optional[str] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category_id: int
    category: Optional[CategoryOut] = None
    price: Decimal
    discount_percent: int
    final_price: Decimal
    stock_qty: int
    warranty_months: Optional[int] = None
    compatibility_notes: Optional[str] = None
    rating_avg: Optional[Decimal] = None
    rating_count: int = 0
    is_demonstration: bool = True
    images: list[ProductImageOut] = Field(default_factory=list)
    seller_name: Optional[str] = None
    seller_verified: bool = False


class CompatibilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    manufacturer: str
    model: str
    variant: Optional[str] = None
    notes: Optional[str] = None


class ProductDetailOut(ProductOut):
    compatibility: list[CompatibilityOut] = Field(default_factory=list)


class CompatibleProductsResponse(BaseModel):
    motorcycle_id: int
    bike_label: str
    match_confidence: str  # "explicit" | "unknown"
    warning: Optional[str] = None
    products: list[ProductOut]


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, le=99)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    product: ProductOut


class CartOut(BaseModel):
    id: int
    items: list[CartItemOut]
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    item_count: int


class DeliveryInfo(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(min_length=10, max_length=20)
    line1: str = Field(min_length=1, max_length=255)
    line2: Optional[str] = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=120)
    pincode: str

    @field_validator("pincode")
    @classmethod
    def _pin(cls, v: str) -> str:
        if not _PINCODE.match(v.strip()):
            raise ValueError("Enter a valid 6-digit Indian PIN code")
        return v.strip()


class OrderCreate(BaseModel):
    delivery: DeliveryInfo
    payment_method: str = Field(default="cod", pattern="^(cod|development)$")


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: Optional[int] = None
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    payment_method: str
    subtotal: Decimal
    discount_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    delivery_name: str
    delivery_phone: str
    delivery_line1: str
    delivery_line2: Optional[str] = None
    delivery_city: str
    delivery_state: str
    delivery_pincode: str
    is_demonstration: bool = True
    created_at: datetime
    items: list[OrderItemOut] = Field(default_factory=list)
