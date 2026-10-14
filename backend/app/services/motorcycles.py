"""Motorcycle ownership helpers."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Motorcycle


def get_owned_motorcycle(db: Session, user_id: int, motorcycle_id: int) -> Motorcycle:
    """Fetch a motorcycle enforcing ownership. Raises NotFound (not Forbidden)
    so we never reveal the existence of another user's private records."""
    moto = db.execute(
        select(Motorcycle).where(
            Motorcycle.id == motorcycle_id, Motorcycle.user_id == user_id
        )
    ).scalar_one_or_none()
    if moto is None:
        raise NotFoundError("Motorcycle not found")
    return moto
