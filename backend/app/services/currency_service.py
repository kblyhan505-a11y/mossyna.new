"""
MOSSYNA BACKEND — Döviz Kuru Servisi

Sorumluluklar:
  1. TCMB günlük kur XML servisinden USD/EUR satış kurunu çekmek
     (birincil kaynak). Erişilemezse yedek bir Forex API'sine düşmek.
  2. Çekilen kuru `exchange_rates` tablosuna yeni bir kayıt olarak yazmak
     (geçmiş kur takibi için — bkz. admin panelindeki "Kur Geçmişi" tablosu).
  3. `price_override = False` olan tüm aktif ürünlerin `price_try` alanını
     yeni kura göre yeniden hesaplamak:
         price_try = base_price_usd * usd_rate * (1 + margin_percentage / 100)
  4. Admin panelindeki "Kuru Şimdi Güncelle" butonu ve günlük otomatik
     zamanlanmış görev (bkz. scheduler.py) bu servisi çağırır.

Bu modül, admin/js/products-admin.js ve admin/exchange-rate.html içindeki
frontend demosunun (localStorage tabanlı) birebir backend karşılığıdır.
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app import models

logger = logging.getLogger("mossyna.currency")
settings = get_settings()


@dataclass
class FetchedRates:
    usd_to_try: float
    eur_to_try: float
    source: str


def _fetch_from_tcmb() -> FetchedRates:
    """TCMB günlük kur XML'inden USD ve EUR 'ForexSelling' (efektif satış) değerlerini okur."""
    response = httpx.get(settings.tcmb_rate_xml_url, timeout=10.0)
    response.raise_for_status()
    root = ET.fromstring(response.content)

    rates: dict[str, float] = {}
    for currency_node in root.findall("Currency"):
        code = currency_node.get("CurrencyCode")
        if code in ("USD", "EUR"):
            selling_text = currency_node.findtext("ForexSelling")
            if selling_text:
                rates[code] = float(selling_text.replace(",", "."))

    if "USD" not in rates or "EUR" not in rates:
        raise ValueError("TCMB yanıtında USD/EUR kuru bulunamadı.")

    return FetchedRates(usd_to_try=rates["USD"], eur_to_try=rates["EUR"], source="TCMB")


def _fetch_from_fallback_api() -> FetchedRates:
    """TCMB erişilemediğinde kullanılan yedek Forex API'si (USD bazlı, TRY/EUR çapraz kur)."""
    response = httpx.get(settings.fallback_rate_api_url, timeout=10.0)
    response.raise_for_status()
    data = response.json()
    # Beklenen format: {"rates": {"TRY": 34.20, "EUR": 0.92}, "base": "USD", ...}
    usd_to_try = float(data["rates"]["TRY"])
    usd_to_eur = float(data["rates"]["EUR"])
    eur_to_try = usd_to_try / usd_to_eur if usd_to_eur else usd_to_try * 1.08
    return FetchedRates(usd_to_try=usd_to_try, eur_to_try=eur_to_try, source="FallbackAPI")


def fetch_current_rates() -> FetchedRates:
    """TCMB'yi dener, başarısız olursa yedek API'ye düşer."""
    try:
        return _fetch_from_tcmb()
    except Exception as exc:  # noqa: BLE001 — kasıtlı geniş yakalama: herhangi bir hata yedeğe düşmeli
        logger.warning("TCMB kur servisi başarısız (%s), yedek API deneniyor…", exc)
        return _fetch_from_fallback_api()


def recalculate_product_prices(db: Session, usd_rate: float) -> tuple[int, float]:
    """
    price_override=False olan tüm aktif ürünlerin price_try alanını yeniden hesaplar.
    Dönüş: (güncellenen ürün sayısı, ortalama yüzdesel değişim)
    """
    products = db.scalars(
        select(models.Product).where(
            models.Product.price_override.is_(False),
            models.Product.is_active.is_(True),
        )
    ).all()

    updated_count = 0
    total_delta_pct = 0.0

    for product in products:
        old_price = float(product.price_try)
        new_price = round(float(product.base_price_usd) * usd_rate * (1 + float(product.margin_percentage) / 100), 2)
        if new_price != old_price:
            if old_price:
                total_delta_pct += ((new_price - old_price) / old_price) * 100
            updated_count += 1
        product.price_try = new_price

    db.commit()
    avg_delta = (total_delta_pct / updated_count) if updated_count else 0.0
    return updated_count, round(avg_delta, 2)


def refresh_exchange_rates(db: Session) -> dict:
    """
    Ana giriş noktası: kuru çeker, veritabanına kaydeder, ürün fiyatlarını
    yeniden hesaplar. Hem admin router'ı hem de zamanlanmış görev (scheduler)
    bu fonksiyonu çağırır.
    """
    rates = fetch_current_rates()

    db.add(models.ExchangeRate(currency_code="USD", rate_to_try=rates.usd_to_try, source=rates.source))
    db.add(models.ExchangeRate(currency_code="EUR", rate_to_try=rates.eur_to_try, source=rates.source))
    db.commit()

    updated_count, avg_delta = recalculate_product_prices(db, rates.usd_to_try)

    logger.info(
        "Kur güncellendi (kaynak=%s): USD=%.4f EUR=%.4f — %d ürün fiyatı yeniden hesaplandı (ort. değişim %%%.2f)",
        rates.source, rates.usd_to_try, rates.eur_to_try, updated_count, avg_delta,
    )

    return {
        "usd_rate": rates.usd_to_try,
        "eur_rate": rates.eur_to_try,
        "source": rates.source,
        "products_updated": updated_count,
        "average_price_change_percent": avg_delta,
    }


def get_latest_rate(db: Session, currency_code: str) -> models.ExchangeRate | None:
    return db.scalars(
        select(models.ExchangeRate)
        .where(models.ExchangeRate.currency_code == currency_code)
        .order_by(models.ExchangeRate.fetched_at.desc())
        .limit(1)
    ).first()
