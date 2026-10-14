"""Motorcycle CRUD routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import ValidationError
from app.models import Motorcycle, User
from app.schemas.bike import MotorcycleCreate, MotorcycleOut, MotorcycleUpdate
from app.services import storage
from app.services.motorcycles import get_owned_motorcycle

router = APIRouter(prefix="/motorcycles", tags=["motorcycles"])


@router.get("", response_model=list[MotorcycleOut])
def list_motorcycles(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Motorcycle]:
    rows = db.execute(
        select(Motorcycle)
        .where(Motorcycle.user_id == user.id)
        .order_by(Motorcycle.is_primary.desc(), Motorcycle.created_at.desc())
    ).scalars().all()
    return list(rows)


@router.post("", response_model=MotorcycleOut, status_code=201)
def create_motorcycle(
    payload: MotorcycleCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Motorcycle:
    count = db.execute(
        select(Motorcycle).where(Motorcycle.user_id == user.id)
    ).scalars().all()
    moto = Motorcycle(**payload.model_dump(), user_id=user.id, is_primary=len(count) == 0)
    db.add(moto)
    db.commit()
    db.refresh(moto)
    return moto


@router.get("/{motorcycle_id}", response_model=MotorcycleOut)
def get_motorcycle(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Motorcycle:
    return get_owned_motorcycle(db, user.id, motorcycle_id)


@router.patch("/{motorcycle_id}", response_model=MotorcycleOut)
def update_motorcycle(
    motorcycle_id: int,
    payload: MotorcycleUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Motorcycle:
    moto = get_owned_motorcycle(db, user.id, motorcycle_id)
    data = payload.model_dump(exclude_unset=True)
    make_primary = data.pop("is_primary", None)
    for field, value in data.items():
        setattr(moto, field, value)
    if make_primary:
        for other in db.execute(
            select(Motorcycle).where(Motorcycle.user_id == user.id)
        ).scalars():
            other.is_primary = other.id == moto.id
    db.commit()
    db.refresh(moto)
    return moto


@router.post("/{motorcycle_id}/image", response_model=MotorcycleOut)
def upload_bike_image(
    motorcycle_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Motorcycle:
    moto = get_owned_motorcycle(db, user.id, motorcycle_id)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise ValidationError("Bike image must be an image")
    key, _ = storage.save_bytes(
        category="bike_images",
        content=file.file.read(),
        content_type=file.content_type if file.content_type in ("image/jpeg", "image/png") else "image/jpeg",
        original_name=file.filename or "bike",
    )
    moto.image_path = key
    db.commit()
    db.refresh(moto)
    return moto


@router.delete("/{motorcycle_id}", status_code=204)
def delete_motorcycle(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    moto = get_owned_motorcycle(db, user.id, motorcycle_id)
    for doc in list(moto.documents):
        storage.delete(doc.storage_key)
    if moto.image_path:
        storage.delete(moto.image_path)
    was_primary = moto.is_primary
    db.delete(moto)
    db.commit()
    if was_primary:
        remaining = db.execute(
            select(Motorcycle).where(Motorcycle.user_id == user.id).order_by(Motorcycle.created_at)
        ).scalars().first()
        if remaining:
            remaining.is_primary = True
            db.commit()
