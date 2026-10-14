"""Cart routes. All totals are computed on the server."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.models import CartItem, Product, User
from app.schemas.shop import CartItemAdd, CartItemUpdate, CartOut
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartOut:
    cart = cart_service.get_or_create_cart(db, user)
    items = cart_service.load_items(db, cart)
    return cart_service.serialize_cart(cart, items)


@router.post("/items", response_model=CartOut, status_code=201)
def add_item(
    payload: CartItemAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    cart = cart_service.get_or_create_cart(db, user)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise NotFoundError("Product not found")
    if product.stock_qty <= 0:
        raise ValidationError("This product is out of stock")

    existing = db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id, CartItem.product_id == product.id
        )
    ).scalar_one_or_none()
    new_qty = payload.quantity + (existing.quantity if existing else 0)
    if new_qty > product.stock_qty:
        raise ValidationError(f"Only {product.stock_qty} unit(s) in stock")
    if new_qty > 99:
        raise ValidationError("Maximum quantity per item is 99")

    if existing:
        existing.quantity = new_qty
    else:
        db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=payload.quantity))
    db.commit()
    items = cart_service.load_items(db, cart)
    return cart_service.serialize_cart(cart, items)


@router.patch("/items/{item_id}", response_model=CartOut)
def update_item(
    item_id: int,
    payload: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    cart = cart_service.get_or_create_cart(db, user)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    if item is None:
        raise NotFoundError("Cart item not found")
    if payload.quantity == 0:
        db.delete(item)
    else:
        product = db.get(Product, item.product_id)
        if product is None:
            raise NotFoundError("Product not found")
        if payload.quantity > product.stock_qty:
            raise ValidationError(f"Only {product.stock_qty} unit(s) in stock")
        item.quantity = payload.quantity
    db.commit()
    items = cart_service.load_items(db, cart)
    return cart_service.serialize_cart(cart, items)


@router.delete("/items/{item_id}", response_model=CartOut)
def remove_item(
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    cart = cart_service.get_or_create_cart(db, user)
    item = db.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    ).scalar_one_or_none()
    if item is None:
        raise NotFoundError("Cart item not found")
    db.delete(item)
    db.commit()
    items = cart_service.load_items(db, cart)
    return cart_service.serialize_cart(cart, items)


@router.delete("", status_code=status.HTTP_200_OK, response_model=CartOut)
def clear_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CartOut:
    cart = cart_service.get_or_create_cart(db, user)
    for item in cart_service.load_items(db, cart):
        db.delete(item)
    db.commit()
    return cart_service.serialize_cart(cart, [])
