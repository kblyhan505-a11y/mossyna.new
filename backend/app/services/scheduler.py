"""
MOSSYNA BACKEND — Zamanlanmış Görevler (APScheduler)

Şu an tek bir görev var: günlük döviz kuru güncellemesi. Admin panelindeki
"Kuru her gün otomatik güncelle (09:00)" anahtarının backend karşılığıdır.

Not: Çoklu worker/instance ile production'da çalıştırılıyorsa (ör. Gunicorn
birden fazla worker ile), bu zamanlayıcının yalnızca TEK bir process'te
başlatıldığından emin olunmalıdır (ör. Celery Beat'e taşımak veya bir
dağıtık kilit (Redis lock) kullanmak production için önerilir).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.services.currency_service import refresh_exchange_rates

logger = logging.getLogger("mossyna.scheduler")
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


def _scheduled_rate_refresh_job() -> None:
    db = SessionLocal()
    try:
        result = refresh_exchange_rates(db)
        logger.info("Zamanlanmış kur güncellemesi tamamlandı: %s", result)
    except Exception:  # noqa: BLE001
        logger.exception("Zamanlanmış kur güncellemesi başarısız oldu.")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    _scheduler.add_job(
        _scheduled_rate_refresh_job,
        trigger="cron",
        hour=settings.exchange_rate_auto_update_hour,
        minute=settings.exchange_rate_auto_update_minute,
        id="daily_exchange_rate_refresh",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Zamanlayıcı başlatıldı: kur her gün %02d:%02d'de otomatik güncellenecek.",
        settings.exchange_rate_auto_update_hour, settings.exchange_rate_auto_update_minute,
    )
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
