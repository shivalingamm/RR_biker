"""Order routes.

Prices and totals are always recomputed on the server from the database. The
client-supplied cart price is never trusted. Stock is validated and decremented
atomically. An optional ``Idempotency-Key`` header prevents duplicate orders.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.models import Notification, Order, OrderItem, Product, User
from app.schemas.common import Page
from app.schemas.shop import OrderCreate, OrderOut
from app.services import cart as cart_service

router = APIRouter(prefix="/orders", tags=["orders"])


def _order_query():
    return select(Order).options(selectinload(Order.items))


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    if idempotency_key:
        existing = db.execute(
            select(Order).where(Order.idempotency_key == idempotency_key, Order.user_id == user.id)
        ).scalar_one_or_none()
        if existing:
            return existing

    cart = cart_service.get_or_create_cart(db, user)
    items = cart_service.load_items(db, cart)
    if not items:
        raise ValidationError("Your cart is empty")

    # Re-validate stock and compute totals from database values only.
    for item in items:
        product = db.get(Product, item.product_id)
        if product is None:
            raise ValidationError("A product in your cart is no longer available")
        if item.quantity > product.stock_qty:
            raise ValidationError(
                f"'{product.name}' only has {product.stock_qty} unit(s) left"
            )

    totals = cart_service.compute_totals(items)

    order = Order(
        user_id=user.id,
        status="confirmed",
        payment_method=payload.payment_method,
        subtotal=totals["subtotal"],
        discount_total=totals["discount_total"],
        shipping_total=totals["shipping_total"],
        grand_total=totals["grand_total"],
        delivery_name=payload.delivery.name,
        delivery_phone=payload.delivery.phone,
        delivery_line1=payload.delivery.line1,
        delivery_line2=payload.delivery.line2,
        delivery_city=payload.delivery.city,
        delivery_state=payload.delivery.state,
        delivery_pincode=payload.delivery.pincode,
        idempotency_key=idempotency_key,
        is_demonstration=True,
    )
    db.add(order)
    db.flush()

    for item in items:
        product = db.get(Product, item.product_id)
        unit = product.final_price
        order.items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                unit_price=unit,
                quantity=item.quantity,
                line_total=(unit * item.quantity).quantize(Decimal("0.01")),
            )
        )
        product.stock_qty -= item.quantity
        db.delete(item)

    db.add(
        Notification(
            user_id=user.id,
            title=f"Order #{order.id} confirmed",
            body=f"Your order of {totals['grand_total']} was placed successfully.",
            category="order",
            link_path=f"/orders/{order.id}",
        )
    )
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=Page[OrderOut])
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[OrderOut]:
    from sqlalchemy import func

    total = db.execute(
        select(func.count(Order.id)).where(Order.user_id == user.id)
    ).scalar_one()
    rows = db.execute(
        _order_query()
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()
    pages = max(1, (total + page_size - 1) // page_size)
    return Page[OrderOut](
        items=[OrderOut.model_validate(o) for o in rows],
        total=total, page=page, page_size=page_size, pages=pages,
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Order:
    order = db.execute(
        _order_query().where(Order.id == order_id, Order.user_id == user.id)
    ).scalar_one_or_none()
    if order is None:
        raise NotFoundError("Order not found")
    return order
