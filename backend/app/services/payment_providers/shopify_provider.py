"""
MOSSYNA BACKEND — Shopify Headless Ödeme Entegrasyonu (Storefront Cart API)

Mimari: Mossyna'nın kendi arayüzü, veritabanı ve admin paneli ürün/fiyat/stok/B2B
mantığının TEK kaynağıdır (source of truth). Shopify SADECE ödemenin güvenle
alındığı, Shopify'ın barındırdığı checkout sayfasıdır — Shopify hiçbir zaman
Mossyna'nın kendi kataloğunu veya fiyatlarını yönetmez.

Bunun çalışması için, her ürünün Shopify tarafında da (elle) bir karşılığı
oluşturulmalı ve o varyantın ID'si admin panelinde ürünün "Shopify Variant ID"
alanına yapıştırılmalıdır (bkz. admin/products.html, products.shopify_variant_id).

Akış:
  1. Müşteri "Ödeme Yap"a bastığında backend, sipariş kalemlerini Shopify ürün
     varyant ID'lerine eşleyerek Storefront API'nin `cartCreate` mutation'ını
     çağırır (bkz. https://shopify.dev/docs/api/storefront/latest/mutations/cartCreate).
     NOT: Eski `checkoutCreate` mutation'ı Shopify tarafından kullanımdan
     kaldırılmıştır; güncel (2024 sonrası) yöntem `cartCreate` + dönen
     `cart.checkoutUrl`dur.
  2. Dönen `cart.checkoutUrl` frontend'e döndürülür; frontend tarayıcıyı bu
     adrese yönlendirir (bkz. frontend/checkout.html) — kart bilgisi hiçbir
     zaman Mossyna sunucusuna dokunmaz.
  3. Müşteri ödemeyi Shopify'ın kendi güvenli sayfasında tamamlar.
  4. Shopify, ödemesi onaylanan siparişi `orders/paid` webhook'u ile
     POST /api/payments/webhook/shopify ucuna bildirir; istek gövdesi
     X-Shopify-Hmac-Sha256 başlığındaki imza ile doğrulanır (bkz.
     https://shopify.dev/docs/apps/build/webhooks/verify-deliveries).
     Mossyna siparişiyle eşleştirme, cartCreate sırasında sepete yazılan
     `note` alanına konan Mossyna sipariş numarası (order_number) üzerinden
     yapılır — Shopify bu notu doğrudan oluşturduğu siparişe aktarır.

Kurulum notu (backend/.env — bkz. .env.example):
  SHOPIFY_STORE_DOMAIN, SHOPIFY_STOREFRONT_ACCESS_TOKEN, SHOPIFY_WEBHOOK_SECRET
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

CART_CREATE_MUTATION = """
mutation MossynaCartCreate($input: CartInput!) {
  cartCreate(input: $input) {
    cart {
      id
      checkoutUrl
    }
    userErrors {
      field
      message
    }
  }
}
"""


class ShopifyProvider(PaymentProvider):
    name = "shopify"

    def _graphql_endpoint(self) -> str:
        return f"https://{settings.shopify_store_domain}/api/{settings.shopify_api_version}/graphql.json"

    def initiate(self, order: models.Order, *, customer_ip: str, customer_email: str) -> PaymentInitiationResult:
        if not settings.shopify_store_domain or not settings.shopify_storefront_access_token:
            raise RuntimeError(
                "Shopify bağlantısı henüz yapılandırılmadı (mağaza adresi veya erişim belirteci eksik). "
                "Lütfen backend/.env dosyasındaki SHOPIFY_STORE_DOMAIN ve "
                "SHOPIFY_STOREFRONT_ACCESS_TOKEN alanlarını doldurun."
            )

        # --- Sipariş kalemlerini Shopify varyant ID'lerine eşle ---
        missing_products: list[str] = []
        lines = []
        for item in order.items:
            variant_id = item.product.shopify_variant_id if item.product else None
            if not variant_id:
                missing_products.append(item.product_name_snapshot)
                continue
            lines.append({"merchandiseId": variant_id, "quantity": item.quantity})

        if missing_products:
            raise RuntimeError(
                "Şu ürün(ler)in Shopify Variant ID'si tanımlı değil, ödemeye geçilemiyor: "
                + ", ".join(missing_products)
                + ". Admin panelinden Ürünler > ilgili ürünü düzenle > 'Shopify Variant ID' "
                "alanını doldurup tekrar deneyin."
            )

        variables = {
            "input": {
                "lines": lines,
                # Shopify'da oluşacak siparişi Mossyna sipariş numarasıyla eşlemek için —
                # webhook'ta bu not okunarak orders.order_number ile eşleştirilir (aşağıda parse_webhook).
                "note": order.order_number,
                "buyerIdentity": {"email": customer_email},
            }
        }

        try:
            response = httpx.post(
                self._graphql_endpoint(),
                json={"query": CART_CREATE_MUTATION, "variables": variables},
                headers={
                    "Content-Type": "application/json",
                    # Not: Shopify artık Storefront API belirteçlerini "Headless" satış kanalı
                    # üzerinden veriyor ve sunucu-taraflı (private) belirteçler farklı bir
                    # header ile gönderiliyor — eski "X-Shopify-Storefront-Access-Token"
                    # (client-taraflı/public belirteçler içindir) DEĞİL. Bkz. .env.example.
                    "Shopify-Storefront-Private-Token": settings.shopify_storefront_access_token,
                },
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Shopify'a bağlanılamadı: {exc}") from exc

        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"Shopify API hatası: {payload['errors']}")

        result = payload["data"]["cartCreate"]
        if result["userErrors"]:
            messages = "; ".join(e["message"] for e in result["userErrors"])
            raise RuntimeError(f"Shopify sepeti oluşturulamadı: {messages}")

        cart = result["cart"]
        return PaymentInitiationResult(
            # Mossyna order_number'ı sağlayıcı referansı olarak kullanılır ki webhook
            # geldiğinde payments.provider_txn_id ile aynı değer üzerinden eşleşsin
            # (bkz. routers/payments.py _finalize_payment).
            provider_reference=order.order_number,
            client_payload={"shopify_checkout_url": cart["checkoutUrl"]},
        )

    def parse_webhook(self, raw_body: bytes, headers: dict, form_data: dict | None = None) -> WebhookParseResult:
        received_hmac = headers.get("x-shopify-hmac-sha256", "")
        if not settings.shopify_webhook_secret or not received_hmac:
            return WebhookParseResult(is_valid=False, provider_reference=None, status="failed", raw_payload={})

        expected_hmac = base64.b64encode(
            hmac.new(settings.shopify_webhook_secret.encode(), raw_body, hashlib.sha256).digest()
        ).decode()

        if not hmac.compare_digest(expected_hmac, received_hmac):
            return WebhookParseResult(is_valid=False, provider_reference=None, status="failed", raw_payload={})

        try:
            data = json.loads(raw_body or b"{}")
        except ValueError:
            return WebhookParseResult(is_valid=False, provider_reference=None, status="failed", raw_payload={})

        # cartCreate sırasında sepete yazılan not (Mossyna sipariş numarası), Shopify
        # tarafından oluşan siparişin `note` alanına aynen aktarılır.
        order_number = (data.get("note") or "").strip()
        financial_status = data.get("financial_status", "")

        return WebhookParseResult(
            is_valid=True,
            provider_reference=order_number or None,
            status="success" if financial_status == "paid" else "failed",
            raw_payload=data,
        )


shopify_provider = ShopifyProvider()
