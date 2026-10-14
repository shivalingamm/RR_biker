"""Private motorcycle document routes.

Documents are stored privately. The API never returns a public URL; the file
is streamed only to the authenticated owner through ``/documents/{id}/file``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.models import DOCUMENT_TYPES, Motorcycle, MotorcycleDocument, User
from app.schemas.bike import DocumentOut, DocumentUpdate
from app.services import storage
from app.services.motorcycles import get_owned_motorcycle

router = APIRouter(prefix="/motorcycles/{motorcycle_id}/documents", tags=["documents"])


def _get_owned_document(db: Session, user_id: int, motorcycle_id: int, document_id: int) -> MotorcycleDocument:
    doc = db.execute(
        select(MotorcycleDocument)
        .join(Motorcycle, Motorcycle.id == MotorcycleDocument.motorcycle_id)
        .where(
            MotorcycleDocument.id == document_id,
            MotorcycleDocument.motorcycle_id == motorcycle_id,
            Motorcycle.user_id == user_id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document not found")
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(
    motorcycle_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MotorcycleDocument]:
    get_owned_motorcycle(db, user.id, motorcycle_id)
    rows = db.execute(
        select(MotorcycleDocument)
        .where(MotorcycleDocument.motorcycle_id == motorcycle_id)
        .order_by(MotorcycleDocument.created_at.desc())
    ).scalars().all()
    return list(rows)


@router.post("", response_model=DocumentOut, status_code=201)
def upload_document(
    motorcycle_id: int,
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    issued_date: str | None = Form(default=None),
    expiry_date: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MotorcycleDocument:
    get_owned_motorcycle(db, user.id, motorcycle_id)
    if doc_type not in DOCUMENT_TYPES:
        raise ValidationError(f"doc_type must be one of {DOCUMENT_TYPES}")

    content = file.file.read()
    key, size = storage.save_bytes(
        category="documents",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        original_name=file.filename or "document",
    )

    def _parse_date(value: str | None):
        if not value:
            return None
        from datetime import date as _date
        try:
            return _date.fromisoformat(value)
        except ValueError:
            raise ValidationError(f"Invalid date '{value}', expected YYYY-MM-DD")

    doc = MotorcycleDocument(
        motorcycle_id=motorcycle_id,
        doc_type=doc_type,
        issued_date=_parse_date(issued_date),
        expiry_date=_parse_date(expiry_date),
        storage_key=key,
        file_name=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        notes=notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    motorcycle_id: int,
    document_id: int,
    payload: DocumentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MotorcycleDocument:
    doc = _get_owned_document(db, user.id, motorcycle_id, document_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{document_id}/file")
def download_document(
    motorcycle_id: int,
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc = _get_owned_document(db, user.id, motorcycle_id, document_id)
    content = storage.read_bytes(doc.storage_key)
    return Response(
        content=content,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{doc.file_name}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    motorcycle_id: int,
    document_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    doc = _get_owned_document(db, user.id, motorcycle_id, document_id)
    storage.delete(doc.storage_key)
    db.delete(doc)
    db.commit()
