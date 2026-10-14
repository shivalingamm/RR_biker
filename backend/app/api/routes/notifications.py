"""In-app notification routes."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError
from app.models import Notification, User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: Notification) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "body": n.body,
        "category": n.category,
        "link_path": n.link_path,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
def list_notifications(
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc()).limit(100)
    return [_serialize(n) for n in db.execute(stmt).scalars().all()]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    n = db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    ).scalar_one_or_none()
    if n is None:
        raise NotFoundError("Notification not found")
    n.is_read = True
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    return _serialize(n)


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(Notification).where(
            Notification.user_id == user.id, Notification.is_read.is_(False)
        )
    ).scalars().all()
    for n in rows:
        n.is_read = True
        n.read_at = now
    db.commit()
    return {"updated": len(rows)}
