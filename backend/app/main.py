"""
MOSSYNA BACKEND — FastAPI Uygulama Girişi

Çalıştırma (geliştirme ortamı):
    uvicorn app.main:app --reload --port 8000

API dokümantasyonu otomatik olarak şurada oluşur:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import Base, engine
from app.services.scheduler import start_scheduler, stop_scheduler
from app.routers import auth, admin_auth, products, orders, payments, exchange_rate, contact, about

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlangıç: tablo oluşturma (yalnızca geliştirme için — production'da Alembic migration kullanılmalı)
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    # Kapanış
    stop_scheduler()


app = FastAPI(
    title="Mossyna API",
    description="Mossyna ev tekstili e-ticaret platformu — REST API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(exchange_rate.router)
app.include_router(contact.router)
app.include_router(about.router)

# Ürün görselleri /media altında servis edilir (bkz. routers/products.py görsel yükleme ucu)
Path(settings.media_root).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_root), name="media")


@app.get("/api/health", tags=["Sistem"])
def health_check():
    return {"status": "ok", "environment": settings.environment}
