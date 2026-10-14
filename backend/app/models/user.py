"""User and profile models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["UserProfile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    motorcycles: Mapped[list["Motorcycle"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    cart: Mapped[Optional["Cart"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_path: Mapped[Optional[str]] = mapped_column(String(500))
    city: Mapped[Optional[str]] = mapped_column(String(120))
    locale: Mapped[str] = mapped_column(String(20), default="en-IN", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    preferred_units: Mapped[str] = mapped_column(String(20), default="metric", nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")

    __table_args__ = (UniqueConstraint("user_id", name="uq_user_profile_user"),)
