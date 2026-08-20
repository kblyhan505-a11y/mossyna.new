"""
MOSSYNA BACKEND — Ödeme Sağlayıcı Arayüzü (Adapter Pattern)

docs/architecture.md §6'da tarif edilen mimari: her sağlayıcı (PayTR,
Stripe, ...) bu ortak arayüzü uygular. `routers/payments.py` sağlayıcıyı
seçer ama HANGİ sağlayıcı olduğunu bilmeden `initiate()` ve
`parse_webhook()` çağırır — yeni bir sağlayıcı eklemek (ör. Iyzico)
sadece bu arayüzü uygulayan yeni bir sınıf yazmayı gerektirir.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app import models


@dataclass
class PaymentInitiationResult:
    """initiate() çağrısının dönüşü — provider'a özgü alanlar opsiyoneldir."""
    provider_reference: str          # PayTR merchant_oid, Stripe payment_intent.id vb.
    client_payload: dict             # Frontend'in ihtiyaç duyduğu veriler (token/client_secret)


@dataclass
class WebhookParseResult:
    """Webhook doğrulama sonucu."""
    is_valid: bool
    provider_reference: str | None
    status: str                      # "success" | "failed"
    raw_payload: dict


class PaymentProvider(ABC):
    """Tüm ödeme sağlayıcı adaptörlerinin uyması gereken sözleşme."""

    name: str

    @abstractmethod
    def initiate(self, order: models.Order, *, customer_ip: str, customer_email: str) -> PaymentInitiationResult:
        """Ödeme sürecini başlatır (token/iframe/payment-intent oluşturur)."""
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, raw_body: bytes, headers: dict, form_data: dict | None = None) -> WebhookParseResult:
        """Sağlayıcıdan gelen webhook/bildirim isteğini doğrular ve normalize eder."""
        raise NotImplementedError
