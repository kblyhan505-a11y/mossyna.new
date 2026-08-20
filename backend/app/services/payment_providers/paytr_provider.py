"""
MOSSYNA BACKEND — PayTR Sanal POS Entegrasyonu (Yurt İçi Kartlar)

PayTR "iFrame API" akışı:
  1. Backend, sipariş bilgileriyle bir `paytr_token` üretir (HMAC-SHA256
     imzalı) ve PayTR'nin `get-token` ucuna gönderir.
  2. PayTR bir `token` döner; frontend bu token ile
     `https://www.paytr.com/odeme/guvenli/{token}` iframe'ini açar.
  3. Ödeme sonucunda PayTR, `PAYTR_NOTIFICATION_URL`'e (bkz. .env) bir
     webhook POST'u atar; bu istek `merchant_key` ile HMAC doğrulanmalıdır.

Referans: https://dev.paytr.com/iframe-api
"""
import base64
import hashlib
import hmac
import json

import httpx

from app.config import get_settings
from app import models
from app.services.payment_providers.base import PaymentProvider, PaymentInitiationResult, WebhookParseResult

settings = get_settings()

PAYTR_GET_TOKEN_URL = "https://www.paytr.com/odeme/api/get-token"


class PayTRProvider(PaymentProvider):
    name = "paytr"

    def _build_hash_str(self, *parts: str) -> str:
        return "".join(parts)

    def _sign(self, hash_str: str) -> str:
        return base64.b64encode(
            hmac.new(settings.paytr_merchant_key.encode(), hash_str.encode(), hashlib.sha256).digest()
        ).decode()

    def initiate(self, order: models.Order, *, customer_ip: str, customer_email: str) -> PaymentInitiationResult:
        merchant_oid = order.order_number.replace("-", "")  # PayTR alfasayısal, tire kabul etmez
        payment_amount_kurus = int(round(float(order.total_amount) * 100))  # PayTR tutarı kuruş cinsinden ister

        user_basket = base64.b64encode(
            json.dumps(
                [[item.product_name_snapshot, str(item.unit_price), item.quantity] for item in order.items]
            ).encode()
        ).decode()

        no_installment = 0
        max_installment = 0
        currency = "TL"
        test_mode = settings.paytr_test_mode

        hash_str = self._build_hash_str(
            settings.paytr_merchant_id,
            customer_ip,
            merchant_oid,
            customer_email,
            str(payment_amount_kurus),
            user_basket,
            str(no_installment),
            str(max_installment),
            currency,
            str(test_mode),
        )
        paytr_token = self._sign(hash_str + settings.paytr_merchant_salt)

        payload = {
            "merchant_id": settings.paytr_merchant_id,
            "user_ip": customer_ip,
            "merchant_oid": merchant_oid,
            "email": customer_email,
            "payment_amount": payment_amount_kurus,
            "paytr_token": paytr_token,
            "user_basket": user_basket,
            "debug_on": 1 if settings.environment != "production" else 0,
            "no_installment": no_installment,
            "max_installment": max_installment,
            "user_name": order.billing_company_name or "Mossyna Müşterisi",
            "user_address": "Teslimat adresi sipariş kaydında mevcuttur.",
            "user_phone": "05000000000",
            "merchant_ok_url": settings.paytr_success_url,
            "merchant_fail_url": settings.paytr_fail_url,
            "timeout_limit": 30,
            "currency": currency,
            "test_mode": test_mode,
        }

        response = httpx.post(PAYTR_GET_TOKEN_URL, data=payload, timeout=15.0)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "success":
            raise RuntimeError(f"PayTR token alınamadı: {result.get('reason', 'bilinmeyen hata')}")

        return PaymentInitiationResult(
            provider_reference=merchant_oid,
            client_payload={"paytr_iframe_token": result["token"]},
        )

    def parse_webhook(self, raw_body: bytes, headers: dict, form_data: dict | None = None) -> WebhookParseResult:
        """
        PayTR webhook'u `application/x-www-form-urlencoded` gönderir:
        merchant_oid, status ("success"|"failed"), total_amount, hash
        """
        data = form_data or {}
        merchant_oid = data.get("merchant_oid", "")
        status = data.get("status", "failed")
        total_amount = data.get("total_amount", "")
        received_hash = data.get("hash", "")

        hash_str = f"{merchant_oid}{settings.paytr_merchant_salt}{status}{total_amount}"
        expected_hash = self._sign(hash_str)

        is_valid = hmac.compare_digest(expected_hash, received_hash)

        return WebhookParseResult(
            is_valid=is_valid,
            provider_reference=merchant_oid,
            status="success" if status == "success" else "failed",
            raw_payload=data,
        )


paytr_provider = PayTRProvider()
