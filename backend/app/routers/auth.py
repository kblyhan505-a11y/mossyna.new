"""
MOSSYNA BACKEND — Müşteri Kimlik Doğrulama (Bireysel / Kurumsal)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app import models, schemas
from app.security import (
    hash_password, verify_password,
    create_customer_access_token, create_customer_refresh_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Müşteri Kimlik Doğrulama"])
settings = get_settings()


def _assign_welcome_discount_if_any(db: Session, user: models.User) -> None:
    """Yeni kayıt olan (e-posta/şifre YA DA Google ile) her kullanıcıya, tanımlıysa
    otomatik hoş geldin kuponunu atar. Hem register() hem google_login() tarafından kullanılır."""
    welcome_discount = db.scalar(
        select(models.Discount).where(models.Discount.is_auto_welcome.is_(True), models.Discount.is_active.is_(True))
    )
    if welcome_discount:
        db.add(models.UserDiscount(user_id=user.id, discount_id=welcome_discount.id))


@router.post("/register", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.CustomerRegisterRequest, db: Session = Depends(get_db)):
    existing = db.scalar(select(models.User).where(models.User.email == payload.email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu e-posta ile kayıtlı bir hesap zaten var.")

    if payload.role == "corporate" and not (payload.company_name and payload.tax_number):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Kurumsal hesaplar için firma adı ve vergi no zorunludur.")

    user = models.User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        role=payload.role,
        company_name=payload.company_name if payload.role == "corporate" else None,
        tax_office=payload.tax_office if payload.role == "corporate" else None,
        tax_number=payload.tax_number if payload.role == "corporate" else None,
    )
    db.add(user)
    db.flush()  # user.id'yi almak için commit beklemeden flush ediyoruz

    # Hoş geldin indirimi: is_auto_welcome=true olan aktif kuponu otomatik ata
    _assign_welcome_discount_if_any(db, user)

    db.commit()
    db.refresh(user)

    return schemas.TokenResponse(
        access_token=create_customer_access_token(user.id, user.role),
        refresh_token=create_customer_refresh_token(user.id),
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.CustomerLoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(models.User).where(models.User.email == payload.email))
    # user.password_hash, yalnızca Google ile kaydolmuş (hiç şifre belirlememiş)
    # hesaplarda None olabilir — bu durumda verify_password'a hiç girmeden
    # net bir "hatalı" sonucu dönülür (passlib None hash ile hata fırlatır).
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-posta veya şifre hatalı.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hesabınız pasif durumda. Lütfen destek ile iletişime geçin.")

    return schemas.TokenResponse(
        access_token=create_customer_access_token(user.id, user.role),
        refresh_token=create_customer_refresh_token(user.id),
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.post("/google", response_model=schemas.TokenResponse)
def google_login(payload: schemas.GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    frontend/js/auth-google.js, Google Identity Services'ten aldığı kimlik
    token'ını ("credential") buraya gönderir. Bu akış OAuth "code exchange"
    DEĞİLDİR — Client Secret gerektirmez; token doğrudan Google'ın genel
    anahtarlarıyla doğrulanır (bkz. GOOGLE_OAUTH_CLIENT_ID ayarı).
    """
    if not settings.google_oauth_client_id:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Google ile giriş henüz yapılandırılmadı. (GOOGLE_OAUTH_CLIENT_ID eksik.)",
        )

    try:
        idinfo = google_id_token.verify_oauth2_token(
            payload.credential, google_requests.Request(), settings.google_oauth_client_id,
        )
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google kimlik doğrulaması başarısız oldu.")

    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    if not google_id or not email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Google hesabından gerekli bilgiler alınamadı.")
    if not idinfo.get("email_verified", False):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Google hesabınızın e-postası doğrulanmamış.")

    user = db.scalar(select(models.User).where(models.User.google_id == google_id))
    if not user:
        # Daha önce e-posta/şifre ile kayıt olmuş olabilir — aynı e-postaysa hesapları
        # birleştir (google_id'yi mevcut hesaba bağla), böylece kullanıcı iki yöntemle de
        # giriş yapabilsin ve yanlışlıkla ikinci bir hesap oluşmasın.
        user = db.scalar(select(models.User).where(models.User.email == email))
        if user:
            user.google_id = google_id
        else:
            user = models.User(
                email=email,
                password_hash=None,
                first_name=idinfo.get("given_name") or "Mossyna",
                last_name=idinfo.get("family_name") or "Müşterisi",
                role="individual",
                google_id=google_id,
                auth_provider="google",
                email_verified_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.flush()
            _assign_welcome_discount_if_any(db, user)

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Hesabınız pasif durumda. Lütfen destek ile iletişime geçin.")

    db.commit()
    db.refresh(user)

    return schemas.TokenResponse(
        access_token=create_customer_access_token(user.id, user.role),
        refresh_token=create_customer_refresh_token(user.id),
    )
