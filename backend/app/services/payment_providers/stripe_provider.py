"""
MOSSYNA BACKEND — Stripe Entegrasyonu (Yurt Dışı Kartlar)

Akış:
  1. Backend bir Stripe PaymentIntent oluşturur ve `client_secret` döner.
  2. Frontend, Stripe.js / Stripe Elements ile bu client_secret'ı kullanarak
     kart bilgisini DOĞRUDAN Stripe'a gönderir (kart verisi hiçbir zaman
     Mossyna sunucusuna dokunmaz — PCI-DSS kapsamını daraltır).
  3. Ödeme sonucu, Stripe'ın `payment_intent.succeeded` webhook event'i ile
     `POST /api/payments/webhook/stripe` ucuna bildirilir; imza
     `STRIPE_WEBHOOK_SECRET` ile doğrulanır.

Referans: https://stripe.com/docs/payments/payment-intents
"""
import stripe

from app.config import get_settings
from app import models
from app.services.payment_providers.base import PaymentProvider, PaymentInitiationResult, WebhookParseResult

settings = get_settings()
stripe.api_key = settings.stripe_secret_key


class StripeProvider(PaymentProvider):
    name = "stripe"

    def initiate(self, order: models.Order, *, customer_ip: str, customer_email: str) -> PaymentInitiationResult:
        # Stripe tutarı "cent" biriminde ister (USD/EUR için en küçük para birimi)
        amount_minor_units = int(round(float(order.total_amount) * 100))

        intent = stripe.PaymentIntent.create(
            amount=amount_minor_units,
            currency=order.currency.lower(),
            receipt_email=customer_email,
            metadata={
                "order_id": order.id,
                "order_number": order.order_number,
            },
            automatic_payment_methods={"enabled": True},
        )

        return PaymentInitiationResult(
            provider_reference=intent.id,
            client_payload={
                "stripe_client_secret": intent.client_secret,
                "stripe_publishable_key": settings.stripe_publishable_key,
            },
        )

    def parse_webhook(self, raw_body: bytes, headers: dict, form_data: dict | None = None) -> WebhookParseResult:
        sig_header = headers.get("stripe-signature", "")
        try:
            event = stripe.Webhook.construct_event(raw_body, sig_header, settings.stripe_webhook_secret)
        except (ValueError, stripe.error.SignatureVerificationError):
            return WebhookParseResult(is_valid=False, provider_reference=None, status="failed", raw_payload={})

        payment_intent = event["data"]["object"]
        is_success = event["type"] == "payment_intent.succeeded"

        return WebhookParseResult(
            is_valid=True,
            provider_reference=payment_intent.get("id"),
            status="success" if is_success else "failed",
            raw_payload=event,
        )


stripe_provider = StripeProvider()
