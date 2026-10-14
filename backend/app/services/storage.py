"""Private file storage.

Files are written to a private directory outside any public static mount.
Access is mediated by authenticated API endpoints that enforce ownership.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.core.errors import ValidationError

_SAFE_EXT = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def _base_dir() -> Path:
    path = Path(settings.storage_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_bytes(
    *,
    category: str,
    content: bytes,
    content_type: str,
    original_name: str,
) -> tuple[str, int]:
    """Persist bytes to private storage. Returns (storage_key, size_bytes)."""
    if not content:
        raise ValidationError("Uploaded file is empty")
    if content_type not in settings.allowed_document_type_list:
        raise ValidationError(
            f"Unsupported file type '{content_type}'. Allowed: {settings.allowed_document_type_list}"
        )
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValidationError(f"File exceeds {settings.max_upload_mb} MB limit")

    ext = _SAFE_EXT.get(content_type) or Path(original_name).suffix.lower() or ".bin"
    key = f"{category}/{uuid.uuid4().hex}{ext}"
    dest = _base_dir() / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return key, len(content)


def path_for(storage_key: str) -> Path:
    """Resolve a storage key to a path, guarding against traversal."""
    base = _base_dir().resolve()
    target = (base / storage_key).resolve()
    if base not in target.parents and target != base:
        raise ValidationError("Invalid storage key")
    return target


def read_bytes(storage_key: str) -> bytes:
    path = path_for(storage_key)
    if not path.exists():
        raise ValidationError("Stored file is missing")
    return path.read_bytes()


def delete(storage_key: str) -> None:
    try:
        path = path_for(storage_key)
    except ValidationError:
        return
    if path.exists():
        path.unlink()


def save_fileobj(*, category: str, fileobj: BinaryIO, content_type: str, original_name: str):
    return save_bytes(
        category=category,
        content=fileobj.read(),
        content_type=content_type,
        original_name=original_name,
    )
