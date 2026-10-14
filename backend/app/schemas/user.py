"""Authentication and user schemas."""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_INDIAN_PHONE = re.compile(r"^(?:\+91[\-\s]?)?[6-9]\d{9}$")


def validate_indian_phone(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    cleaned = value.replace(" ", "").replace("-", "")
    if not _INDIAN_PHONE.match(cleaned):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return cleaned


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    phone: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return validate_indian_phone(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    phone: Optional[str] = None
    display_name: str
    avatar_path: Optional[str] = None
    city: Optional[str] = None
    currency: str = "INR"
    locale: str = "en-IN"


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    phone: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=120)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return validate_indian_phone(v)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)
