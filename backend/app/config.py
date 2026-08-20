"""
MOSSYNA BACKEND — Uygulama Ayarları

Tüm ortam değişkenleri burada tek bir yerden tip güvenli şekilde okunur.
`.env` dosyası proje kökünde (backend/) bulunmalıdır — bkz. `.env.example`.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Veritabanı
    database_url: str = "postgresql://mossyna_user:password@localhost:5432/mossyna_db"

    # JWT
    jwt_secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_audience_customer: str = "mossyna-customer"
    jwt_audience_admin: str = "mossyna-admin"

    # CORS
    cors_origins: str = "http://localhost:5500"

    # Döviz kuru
    tcmb_rate_xml_url: str = "https://www.tcmb.gov.tr/kurlar/today.xml"
    fallback_rate_api_url: str = "https://api.exchangerate.host/latest?base=USD&symbols=TRY,EUR"
    exchange_rate_auto_update_hour: int = 9
    exchange_rate_auto_update_minute: int = 0
    default_product_margin_percentage: float = 40.0

    # PayTR
    paytr_merchant_id: str = ""
    paytr_merchant_key: str = ""
    paytr_merchant_salt: str = ""
    paytr_test_mode: int = 1
    paytr_success_url: str = "https://mossyna.com/checkout/success"
    paytr_fail_url: str = "https://mossyna.com/checkout/failed"
    paytr_notification_url: str = "https://api.mossyna.com/api/payments/webhook/paytr"

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # Shopify (headless ödeme — Mossyna'nın kendi arayüzü sistemin kaynağı kalır,
    # Shopify SADECE ödemenin tamamlandığı güvenli, barındırılan checkout sayfasıdır.
    # bkz. app/services/payment_providers/shopify_provider.py)
    shopify_store_domain: str = ""  # ör. "mossyna.myshopify.com" (https:// OLMADAN)
    shopify_storefront_access_token: str = ""
    shopify_webhook_secret: str = ""
    shopify_api_version: str = "2026-07"

    # Google ile Tek Tık Giriş (Google Identity Services — tarayıcıda üretilen
    # kimlik token'ı doğrudan Google'ın genel anahtarlarıyla doğrulanır; bu akışta
    # Client Secret GEREKMEZ, sadece Client ID yeterlidir. Bu değer,
    # frontend/js/auth-google.js içindeki MOSSYNA_GOOGLE_CLIENT_ID ile
    # BİREBİR AYNI olmalıdır.)
    google_oauth_client_id: str = ""

    # Genel
    environment: str = "development"
    frontend_base_url: str = "https://mossyna.com"
    media_root: str = "media"

    # Görsel Depolama ("local" = backend diski, sadece geliştirme; "s3" = Cloudflare
    # R2 / S3 uyumlu nesne depolama, production ve autoscaling için ZORUNLU — bkz.
    # app/services/storage.py)
    storage_backend: str = "local"
    s3_endpoint_url: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_bucket_name: str = ""
    s3_public_base_url: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Ayarları tek seferlik okuyup önbelleğe alır (uygulama boyunca yeniden okunmaz)."""
    return Settings()
