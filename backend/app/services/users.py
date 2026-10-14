"""User/profile helpers."""
from __future__ import annotations

from app.models import User
from app.schemas.user import UserOut


def user_to_out(user: User) -> UserOut:
    profile = user.profile
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        display_name=profile.display_name if profile else user.email.split("@")[0],
        avatar_path=profile.avatar_path if profile else None,
        city=profile.city if profile else None,
        currency=profile.currency if profile else "INR",
        locale=profile.locale if profile else "en-IN",
    )
