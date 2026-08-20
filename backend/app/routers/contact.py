"""
MOSSYNA BACKEND — İletişim Formu (Public gönderim + Admin yönetimi)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import get_current_admin

router = APIRouter(tags=["İletişim"])


@router.post("/api/contact", response_model=schemas.ContactMessageResponse, status_code=status.HTTP_201_CREATED)
def submit_contact_message(
    payload: schemas.ContactMessageCreateRequest,
    db: Session = Depends(get_db),
):
    """Sitedeki İletişim Formu bu ucu çağırır; kayıt admin panelindeki Mesajlar listesine düşer."""
    message = models.ContactMessage(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        subject=payload.subject,
        message=payload.message,
        status="new",
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/api/admin/messages", response_model=list[schemas.ContactMessageResponse])
def admin_list_messages(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    stmt = select(models.ContactMessage).order_by(models.ContactMessage.created_at.desc())
    if status_filter and status_filter != "all":
        stmt = stmt.where(models.ContactMessage.status == status_filter)
    return db.scalars(stmt).all()


@router.post("/api/admin/messages/{message_id}/read", response_model=schemas.ContactMessageResponse)
def admin_mark_read(message_id: int, db: Session = Depends(get_db), _admin: models.AdminUser = Depends(get_current_admin)):
    message = db.get(models.ContactMessage, message_id)
    if not message:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesaj bulunamadı.")
    if message.status == "new":
        message.status = "read"
        db.commit()
        db.refresh(message)
    return message


@router.post("/api/admin/messages/{message_id}/reply", response_model=schemas.ContactMessageResponse)
def admin_reply_message(
    message_id: int,
    payload: schemas.ContactReplyRequest,
    db: Session = Depends(get_db),
    admin: models.AdminUser = Depends(get_current_admin),
):
    message = db.get(models.ContactMessage, message_id)
    if not message:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesaj bulunamadı.")

    message.admin_reply = payload.reply
    message.status = "replied"
    message.replied_by = admin.id
    message.replied_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)

    # Not: Gerçek sistemde burada müşteriye e-posta bildirimi tetiklenir
    # (ör. bir e-posta servisi/queue'su — SendGrid, SES, Celery task vb.)
    return message
