"""
MOSSYNA BACKEND — Kimlik Doğrulama ve Yetkilendirme

Önemli güvenlik kararı: Müşteri (users) ve yönetici (admin_users) token'ları
FARKLI "aud" (audience) claim'i ile imzalanır. Bu sayede çalınmış/sızmış bir
müşteri token'ı admin uçlarında ASLA kabul edilmez ve tam tersi de geçerlidir.
Bkz. docs/architecture.md §3.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app import models

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


# ---------- Şifre ----------
def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ---------- JWT ----------
def create_token(
    subject: str,
    audience: str,
    expires_delta: timedelta,
    extra_claims: dict | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "aud": audience,
        "iat": now,
        "exp": now + expires_delta,
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_customer_access_token(user_id: str, role: str) -> str:
    return create_token(
        subject=user_id,
        audience=settings.jwt_audience_customer,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        extra_claims={"role": role, "type": "access"},
    )


def create_customer_refresh_token(user_id: str) -> str:
    return create_token(
        subject=user_id,
        audience=settings.jwt_audience_customer,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
        extra_claims={"type": "refresh"},
    )


def create_admin_access_token(admin_id: str, role: str) -> str:
    return create_token(
        subject=admin_id,
        audience=settings.jwt_audience_admin,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
        extra_claims={"role": role, "type": "access"},
    )


def decode_token(token: str, expected_audience: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=expected_audience,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya süresi dolmuş oturum. Lütfen tekrar giriş yapın.",
        )


# ---------- FastAPI Dependencies ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Bireysel/Kurumsal müşteri uçları için oturum doğrulama."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş gerekli.")
    payload = decode_token(credentials.credentials, settings.jwt_audience_customer)
    user = db.get(models.User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kullanıcı bulunamadı.")
    return user


def get_current_corporate_user(user: models.User = Depends(get_current_user)) -> models.User:
    """Sadece kurumsal (B2B) müşterilere açık uçlar için."""
    if user.role != "corporate":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem sadece kurumsal hesaplar içindir.")
    return user


def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.AdminUser:
    """Yönetici paneli uçları için oturum doğrulama (müşteri token'ı burada asla geçerli olmaz)."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yönetici girişi gerekli.")
    payload = decode_token(credentials.credentials, settings.jwt_audience_admin)
    admin = db.get(models.AdminUser, payload["sub"])
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yönetici bulunamadı.")
    return admin


def require_superadmin(admin: models.AdminUser = Depends(get_current_admin)) -> models.AdminUser:
    if admin.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bu işlem için süper yönetici yetkisi gerekir.")
    return admin
