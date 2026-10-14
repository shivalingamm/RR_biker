"""Cart helpers: totals are always computed server-side."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Cart, CartItem, Product, User
from app.schemas.shop import CartItemOut, CartOut
from app.services import products as product_service

SHIPPING_FLAT = Decimal("49.00")
FREE_SHIPPING_THRESHOLD = Decimal("999.00")


def get_or_create_cart(db: Session, user: User) -> Cart:
    cart = db.execute(
        select(Cart).where(Cart.user_id == user.id)
    ).scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def load_items(db: Session, cart: Cart) -> list[CartItem]:
    return list(
        db.execute(
            select(CartItem)
            .where(CartItem.cart_id == cart.id)
            .options(
                selectinload(CartItem.product).selectinload(Product.images),
                selectinload(CartItem.product).selectinload(Product.category),
                selectinload(CartItem.product).selectinload(Product.seller),
            )
            .order_by(CartItem.id)
        ).scalars().all()
    )


def compute_totals(items: list[CartItem]) -> dict:
    subtotal = Decimal("0.00")
    discount_total = Decimal("0.00")
    for item in items:
        product = item.product
        unit = product.final_price
        subtotal += product.price * item.quantity
        discount_total += (product.price - unit) * item.quantity
    after_discount = subtotal - discount_total
    shipping = Decimal("0.00") if after_discount >= FREE_SHIPPING_THRESHOLD or not items else SHIPPING_FLAT
    grand_total = (after_discount + shipping).quantize(Decimal("0.01"))
    return {
        "subtotal": subtotal.quantize(Decimal("0.01")),
        "discount_total": discount_total.quantize(Decimal("0.01")),
        "shipping_total": shipping.quantize(Decimal("0.01")),
        "grand_total": grand_total,
    }


def serialize_cart(cart: Cart, items: list[CartItem]) -> CartOut:
    totals = compute_totals(items)
    out_items = []
    for item in items:
        unit = item.product.final_price
        out_items.append(
            CartItemOut(
                id=item.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=unit,
                line_total=(unit * item.quantity).quantize(Decimal("0.01")),
                product=product_service.serialize_product(item.product),
            )
        )
    return CartOut(
        id=cart.id,
        items=out_items,
        subtotal=totals["subtotal"],
        discount_total=totals["discount_total"],
        shipping_total=totals["shipping_total"],
        grand_total=totals["grand_total"],
        item_count=sum(i.quantity for i in items),
    )
