"""Maintenance history routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models import MaintenanceRecord, User
from app.schemas.bike import MaintenanceCreate, MaintenanceOut, MaintenanceUpdate
from app.services.motorcycles import get_owned_motorcycle

router = APIRouter(prefix="/motorcycles/{motorcycle_id}/maintenance", tags=["maintenance"])


def _get_record(db: Session, motorcycle_id: int, record_id: int) -> MaintenanceRecord:
    record = db.execute(
        select(MaintenanceRecord).where(
            MaintenanceRecord.id == record_id,
            MaintenanceRecord.motorcycle_id == motorcycle_id,
        )
    ).scalar_one_or_none()
    if record is None:
        raise NotFoundError("Maintenance record not found")
    return record


@router.get("", response_model=list[MaintenanceOut])
def list_maintenance(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceRecord]:
    get_owned_motorcycle(db, user.id, motorcycle_id)
    rows = db.execute(
        select(MaintenanceRecord)
        .where(MaintenanceRecord.motorcycle_id == motorcycle_id)
        .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
    ).scalars().all()
    return list(rows)


@router.post("", response_model=MaintenanceOut, status_code=201)
def create_maintenance(
    motorcycle_id: int,
    payload: MaintenanceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRecord:
    moto = get_owned_motorcycle(db, user.id, motorcycle_id)
    record = MaintenanceRecord(**payload.model_dump(), motorcycle_id=moto.id)
    db.add(record)
    # keep odometer reasonably in sync (never decrease it)
    if payload.odometer_km and (moto.odometer_km is None or payload.odometer_km > moto.odometer_km):
        moto.odometer_km = payload.odometer_km
    db.commit()
    db.refresh(record)
    return record


@router.patch("/{record_id}", response_model=MaintenanceOut)
def update_maintenance(
    motorcycle_id: int,
    record_id: int,
    payload: MaintenanceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceRecord:
    get_owned_motorcycle(db, user.id, motorcycle_id)
    record = _get_record(db, motorcycle_id, record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_maintenance(
    motorcycle_id: int,
    record_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    get_owned_motorcycle(db, user.id, motorcycle_id)
    record = _get_record(db, motorcycle_id, record_id)
    db.delete(record)
    db.commit()
