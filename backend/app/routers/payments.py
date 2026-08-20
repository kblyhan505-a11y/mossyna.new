"""
MOSSYNA BACKEND — Ödeme Başlatma ve Webhook Uçları

Sağlayıcı seçimi bir dict üzerinden yapılır (adapter pattern) — yeni bir
sağlayıcı eklemek burada tek satırlık bir kayıt gerektirir.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.payment_providers.paytr_provider import paytr_provider
from app.services.payment_providers.stripe_provider import stripe_provider
from app.services.payment_providers.shopify_provider import shopify_provider
from app.services.payment_providers.base import PaymentProvider

router = APIRouter(prefix="/api/payments", tags=["Ödeme"])

_PROVIDERS: dict[str, PaymentProvider] = {
    "shopify": shopify_provider,
    "paytr": paytr_provider,
    "stripe": stripe_provider,
}


@router.post("/initiate", response_model=schemas.PaymentInitiateResponse)
def initiate_payment(payload: schemas.PaymentInitiateRequest, request: Request, db: Session = Depends(get_db)):
    order = db.get(models.Order, payload.order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sipariş bulunamadı.")
    if order.status not in ("pending", "awaiting_payment"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Bu sipariş için ödeme zaten başlatılmış veya tamamlanmış.")

    # --- Banka Havalesi: sanal POS gerektirmeyen basit yol ---
    if payload.provider == "bank_transfer":
        payment = models.Payment(
            order_id=order.id, provider="bank_transfer", amount=order.total_amount,
            currency=order.currency, status="initiated",
        )
        order.status = "awaiting_payment"
        order.payment_method = "bank_transfer"
        db.add(payment)
        db.commit()
        return schemas.PaymentInitiateResponse(
            payment_id=payment.id, provider="bank_transfer", status=payment.status,
            bank_transfer_iban="TR00 0000 0000 0000 0000 0000 00 — Mossyna Tekstil A.Ş.",
        )

    provider = _PROVIDERS.get(payload.provider)
    if not provider:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Desteklenmeyen ödeme sağlayıcısı.")

    customer_email = order.user.email if order.user else "misafir@mossyna.com"
    customer_ip = request.client.host if request.client else "0.0.0.0"

    try:
        result = provider.initiate(order, customer_ip=customer_ip, customer_email=customer_email)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Ödeme sağlayıcısına bağlanılamadı: {exc}")

    payment = models.Payment(
        order_id=order.id,
        provider=payload.provider,
        provider_txn_id=result.provider_reference,
        amount=order.total_amount,
        currency=order.currency,
        status="initiated",
    )
    order.status = "awaiting_payment"
    order.payment_method = "credit_card"
    order.payment_provider = payload.provider
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return schemas.PaymentInitiateResponse(
        payment_id=payment.id, provider=payload.provider, status=payment.status, **result.client_payload,
    )


def _finalize_payment(db: Session, provider_name: str, provider_reference: str, is_success: bool, raw_payload: dict) -> None:
    payment = db.scalar(
        select(models.Payment).where(
            models.Payment.provider == provider_name,
            models.Payment.provider_txn_id == provider_reference,
        )
    )
    if not payment:
        return  # Bilinmeyen/ilişkisiz webhook — sessizce yoksay

    payment.status = "success" if is_success else "failed"
    payment.raw_response = raw_payload
    order = payment.order
    order.status = "paid" if is_success else "cancelled"
    db.commit()


@router.post("/webhook/paytr")
async def paytr_webhook(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    form_data = dict(form)
    result = paytr_provider.parse_webhook(raw_body=b"", headers=dict(request.headers), form_data=form_data)

    if not result.is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçersiz hash — istek doğrulanamadı.")

    _finalize_payment(db, "paytr", result.provider_reference, result.status == "success", result.raw_payload)

    # PayTR, bildirim ucunun düz metin "OK" döndürmesini ZORUNLU kılar,
    # aksi halde bildirimi başarısız sayıp tekrar tekrar dener.
    return Response(content="OK", media_type="text/plain")


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    result = stripe_provider.parse_webhook(raw_body=raw_body, headers=dict(request.headers))

    if not result.is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Stripe imza doğrulaması başarısız.")

    _finalize_payment(db, "stripe", result.provider_reference, result.status == "success", result.raw_payload)
    return {"received": True}


@router.post("/webhook/shopify")
async def shopify_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Shopify Admin → Ayarlar → Bildirimler → Webhook'lar bölümünden "Sipariş ödemesi
    alındı" (orders/paid) olayı için bu adres tanımlanmalıdır:
    https://<backend-adresiniz>/api/payments/webhook/shopify
    """
    raw_body = await request.body()
    result = shopify_provider.parse_webhook(raw_body=raw_body, headers=dict(request.headers))

    if not result.is_valid:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Shopify imza doğrulaması başarısız.")
    if not result.provider_reference:
        # İmza geçerli ama sipariş notunda Mossyna sipariş numarası bulunamadı —
        # eşleştirilemeyen bir bildirim; sessizce yoksay.
        return {"received": True}

    _finalize_payment(db, "shopify", result.provider_reference, result.status == "success", result.raw_payload)
    return {"received": True}
