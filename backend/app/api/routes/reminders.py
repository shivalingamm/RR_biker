"""Reminder routes plus a dashboard summary used by the home screen."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models import (
    MaintenanceRecord,
    Motorcycle,
    MotorcycleDocument,
    Reminder,
    User,
)
from app.schemas.bike import ReminderCreate, ReminderOut, ReminderUpdate

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    include_done: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Reminder]:
    stmt = select(Reminder).where(Reminder.user_id == user.id)
    if not include_done:
        stmt = stmt.where(Reminder.is_done.is_(False))
    stmt = stmt.order_by(Reminder.due_date.asc().nulls_last(), Reminder.id.desc())
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(
    payload: ReminderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Reminder:
    if payload.motorcycle_id is not None:
        owned = db.execute(
            select(Motorcycle).where(
                Motorcycle.id == payload.motorcycle_id, Motorcycle.user_id == user.id
            )
        ).scalar_one_or_none()
        if owned is None:
            raise NotFoundError("Motorcycle not found")
    reminder = Reminder(**payload.model_dump(), user_id=user.id)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Reminder:
    reminder = db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
    ).scalar_one_or_none()
    if reminder is None:
        raise NotFoundError("Reminder not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reminder, field, value)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(
    reminder_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    reminder = db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user.id)
    ).scalar_one_or_none()
    if reminder is None:
        raise NotFoundError("Reminder not found")
    db.delete(reminder)
    db.commit()


@router.get("/dashboard")
def dashboard(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Aggregated home-screen summary: primary bike, upcoming reminders, alerts."""
    today = date.today()
    horizon = today + timedelta(days=30)

    bikes = db.execute(
        select(Motorcycle).where(Motorcycle.user_id == user.id)
    ).scalars().all()
    primary = next((b for b in bikes if b.is_primary), bikes[0] if bikes else None)

    reminders = db.execute(
        select(Reminder)
        .where(Reminder.user_id == user.id, Reminder.is_done.is_(False))
        .order_by(Reminder.due_date.asc().nulls_last())
    ).scalars().all()

    upcoming = [
        r for r in reminders
        if r.due_date is not None and today <= r.due_date <= horizon
    ]

    doc_alerts = []
    if bikes:
        docs = db.execute(
            select(MotorcycleDocument).where(
                MotorcycleDocument.motorcycle_id.in_([b.id for b in bikes]),
                MotorcycleDocument.expiry_date.is_not(None),
            )
        ).scalars().all()
        for d in docs:
            if d.expiry_date and today <= d.expiry_date <= horizon:
                days = (d.expiry_date - today).days
                doc_alerts.append({
                    "id": d.id,
                    "motorcycle_id": d.motorcycle_id,
                    "doc_type": d.doc_type,
                    "expiry_date": d.expiry_date.isoformat(),
                    "days_left": days,
                    "expired": d.expiry_date < today,
                })

    last_service = None
    if primary:
        last_service = db.execute(
            select(MaintenanceRecord)
            .where(MaintenanceRecord.motorcycle_id == primary.id)
            .order_by(MaintenanceRecord.service_date.desc())
            .limit(1)
        ).scalar_one_or_none()

    return {
        "bike_count": len(bikes),
        "primary_bike": (
            {
                "id": primary.id,
                "manufacturer": primary.manufacturer,
                "model": primary.model,
                "variant": primary.variant,
                "odometer_km": primary.odometer_km,
                "image_path": primary.image_path,
            }
            if primary
            else None
        ),
        "reminders_due_soon": [
            {"id": r.id, "title": r.title, "due_date": r.due_date.isoformat() if r.due_date else None,
             "category": r.category, "motorcycle_id": r.motorcycle_id}
            for r in upcoming
        ],
        "document_alerts": doc_alerts,
        "last_service": (
            {
                "id": last_service.id,
                "service_date": last_service.service_date.isoformat(),
                "service_type": last_service.service_type,
                "odometer_km": last_service.odometer_km,
            }
            if last_service
            else None
        ),
    }
