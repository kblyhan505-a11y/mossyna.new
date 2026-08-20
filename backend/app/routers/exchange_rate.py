"""
MOSSYNA BACKEND — Döviz Kuru Uçları (Public okuma + Admin yönetimi)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import get_current_admin
from app.services.currency_service import get_latest_rate, refresh_exchange_rates

router = APIRouter(tags=["Döviz Kuru"])


@router.get("/api/exchange-rate/current", response_model=list[schemas.ExchangeRateResponse])
def get_current_rates(db: Session = Depends(get_db)):
    """Checkout sayfasındaki TRY/USD/EUR görüntüleme para birimi seçici bu ucu kullanır."""
    usd = get_latest_rate(db, "USD")
    eur = get_latest_rate(db, "EUR")
    results = [r for r in (usd, eur) if r is not None]
    if not results:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Henüz kur verisi çekilmemiş.")
    return results


@router.get("/api/admin/exchange-rate/history", response_model=list[schemas.ExchangeRateResponse])
def admin_rate_history(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    """Admin panelindeki 'Kur Geçmişi' tablosunun veri kaynağı."""
    return db.scalars(
        select(models.ExchangeRate).order_by(models.ExchangeRate.fetched_at.desc()).limit(limit)
    ).all()


@router.post("/api/admin/exchange-rate/refresh", response_model=schemas.ExchangeRateRefreshResponse)
def admin_refresh_rate(db: Session = Depends(get_db), _admin: models.AdminUser = Depends(get_current_admin)):
    """Admin panelindeki '🔄 Kuru Şimdi Güncelle' butonunun backend karşılığı."""
    try:
        result = refresh_exchange_rates(db)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Kur servisine ulaşılamadı: {exc}")
    return result


@router.post("/api/admin/exchange-rate/manual", response_model=schemas.ExchangeRateRefreshResponse)
def admin_set_manual_rate(
    payload: schemas.ManualRateRequest,
    db: Session = Depends(get_db),
    _admin: models.AdminUser = Depends(get_current_admin),
):
    """TCMB senkronizasyonu geçici olarak erişilemez olduğunda manuel kur girişi."""
    from app.services.currency_service import recalculate_product_prices

    db.add(models.ExchangeRate(currency_code="USD", rate_to_try=payload.usd_rate, source="Manuel"))
    db.add(models.ExchangeRate(currency_code="EUR", rate_to_try=payload.eur_rate, source="Manuel"))
    db.commit()

    updated_count, avg_delta = recalculate_product_prices(db, payload.usd_rate)

    return schemas.ExchangeRateRefreshResponse(
        usd_rate=payload.usd_rate,
        eur_rate=payload.eur_rate,
        source="Manuel",
        products_updated=updated_count,
        average_price_change_percent=avg_delta,
    )
