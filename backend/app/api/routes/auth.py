"""Authentication routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import ConflictError, UnauthorizedError, ValidationError
from app.core.ratelimit import RateLimiter, client_key
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Cart, User, UserProfile
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import storage
from app.services.users import user_to_out

router = APIRouter(prefix="/auth", tags=["auth"])

_auth_limiter = RateLimiter(max_calls=20, window_seconds=60)


def _serialize(user: User) -> UserOut:
    return user_to_out(user)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    _auth_limiter.check(f"register:{client_key(request)}")
    existing = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if existing:
        raise ConflictError("An account with this email already exists")
    if payload.phone:
        phone_used = db.execute(select(User).where(User.phone == payload.phone)).scalar_one_or_none()
        if phone_used:
            raise ConflictError("This phone number is already registered")

    user = User(
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
    )
    user.profile = UserProfile(display_name=payload.display_name.strip())
    user.cart = Cart()
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    _auth_limiter.check(f"login:{client_key(request)}")
    user = db.execute(select(User).where(User.email == payload.email.lower())).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _serialize(user)


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if payload.phone and payload.phone != user.phone:
        clash = db.execute(select(User).where(User.phone == payload.phone, User.id != user.id)).scalar_one_or_none()
        if clash:
            raise ConflictError("This phone number is already registered")
        user.phone = payload.phone
    if user.profile is None:
        user.profile = UserProfile(display_name=user.email.split("@")[0])
    if payload.display_name is not None:
        user.profile.display_name = payload.display_name.strip()
    if payload.city is not None:
        user.profile.city = payload.city
    db.commit()
    db.refresh(user)
    return _serialize(user)


@router.post("/me/avatar", response_model=UserOut)
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise ValidationError("Avatar must be an image")
    content = file.file.read()
    if len(content) > 5 * 1024 * 1024:
        raise ValidationError("Avatar must be under 5 MB")
    key, _ = storage.save_bytes(
        category="avatars", content=content,
        content_type=file.content_type, original_name=file.filename or "avatar",
    )
    if user.profile is None:
        user.profile = UserProfile(display_name=user.email.split("@")[0])
    user.profile.avatar_path = key
    db.commit()
    db.refresh(user)
    return _serialize(user)


@router.post("/change-password", status_code=204)
def change_password(
    payload: PasswordChange,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


@router.delete("/me", status_code=204)
def delete_account(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Account deletion cascades to bikes, documents, cart, orders, reviews."""
    # remove private files first
    for moto in user.motorcycles:
        for doc in moto.documents:
            storage.delete(doc.storage_key)
    if user.profile and user.profile.avatar_path:
        storage.delete(user.profile.avatar_path)
    db.delete(user)
    db.commit()
