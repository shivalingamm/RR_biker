"""Shopping models: sellers, categories, products, compatibility, cart, orders."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

ORDER_STATUSES = ("pending", "confirmed", "shipped", "delivered", "cancelled")


class Seller(Base, TimestampMixin):
    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(120))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # demonstration sellers are clearly flagged and never presented as live
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProductCategory(Base, TimestampMixin):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    seller_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, index=True)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stock_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warranty_months: Mapped[Optional[int]] = mapped_column(Integer)
    compatibility_notes: Mapped[Optional[str]] = mapped_column(Text)
    rating_avg: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[ProductCategory] = relationship(back_populates="products")
    seller: Mapped[Optional[Seller]] = relationship()
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    compatibility: Mapped[list["MotorcycleProductCompatibility"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def final_price(self) -> Decimal:
        if self.discount_percent:
            return (self.price * (Decimal(100) - Decimal(self.discount_percent)) / Decimal(100)).quantize(Decimal("0.01"))
        return self.price.quantize(Decimal("0.01"))


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[Optional[str]] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    product: Mapped[Product] = relationship(back_populates="images")


class MotorcycleProductCompatibility(Base, TimestampMixin):
    """Explicit compatibility records. Never inferred by AI."""

    __tablename__ = "motorcycle_product_compatibility"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    catalogue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("motorcycle_catalogue.id", ondelete="SET NULL"), index=True
    )
    manufacturer: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    variant: Mapped[Optional[str]] = mapped_column(String(120))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="compatibility")

    __table_args__ = (
        UniqueConstraint(
            "product_id", "manufacturer", "model", "variant",
            name="uq_compat_product_bike",
        ),
    )


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="cart")
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    cart: Mapped[Cart] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False, index=True)
    payment_method: Mapped[str] = mapped_column(String(30), default="cod", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    shipping_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    delivery_name: Mapped[str] = mapped_column(String(160), nullable=False)
    delivery_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    delivery_line2: Mapped[Optional[str]] = mapped_column(String(255))
    delivery_city: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_state: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_pincode: Mapped[str] = mapped_column(String(10), nullable=False)

    idempotency_key: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True)
    is_demonstration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    # snapshot fields so historical orders survive product changes
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")

    __table_args__ = (Index("ix_order_item_order", "order_id"),)
