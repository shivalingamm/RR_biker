"""Shared FastAPI dependencies: database session and current user."""
from __future__ import annotations

from typing import Optional

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.security import decode_token
from app.models import User


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid or expired token")
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Invalid token payload")
    user = db.get(User, int(subject))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    return _user_from_token(token, db)


def get_optional_user(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return _user_from_token(authorization.split(" ", 1)[1].strip(), db)
    except UnauthorizedError:
        return None
