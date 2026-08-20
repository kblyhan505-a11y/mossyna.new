"""
MOSSYNA BACKEND — Yönetici Kimlik Doğrulama

Bilerek `routers/auth.py`'den ayrı tutulur: admin girişi tamamen farklı bir
tabloya (admin_users) ve farklı bir JWT audience'ına karşılık gelir.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import verify_password, create_admin_access_token, get_current_admin

router = APIRouter(prefix="/api/admin/auth", tags=["Yönetici Kimlik Doğrulama"])


@router.post("/login", response_model=schemas.TokenResponse)
def admin_login(payload: schemas.AdminLoginRequest, db: Session = Depends(get_db)):
    admin = db.scalar(
        select(models.AdminUser).where(
            (models.AdminUser.username == payload.username) | (models.AdminUser.email == payload.username)
        )
    )
    if not admin or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kullanıcı adı veya şifre hatalı.")
    if not admin.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu yönetici hesabı devre dışı bırakılmış.")

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return schemas.TokenResponse(access_token=create_admin_access_token(admin.id, admin.role))


@router.get("/me", response_model=schemas.AdminResponse)
def get_admin_me(current_admin: models.AdminUser = Depends(get_current_admin)):
    return current_admin


# ---------------------------------------------------------------------
# Not: İlk süper yönetici hesabı `python -m app.scripts.seed` ile oluşturulur
# (bkz. app/scripts/seed.py). Açık bir self-servis admin kayıt ucu KASITLI
# olarak sağlanmaz — yeni admin hesapları sadece mevcut bir süper yönetici
# tarafından (ör. ileride eklenecek POST /api/admin/users ucuyla) oluşturulabilmelidir.
# ---------------------------------------------------------------------
