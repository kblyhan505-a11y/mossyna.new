"""
MOSSYNA BACKEND — Veritabanı Bağlantısı (SQLAlchemy 2.0)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Tüm ORM modellerinin miras aldığı temel sınıf."""
    pass


def get_db():
    """FastAPI dependency: her istek için bir veritabanı oturumu açar ve kapatır."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
