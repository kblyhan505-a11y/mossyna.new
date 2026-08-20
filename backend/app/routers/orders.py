"""
MOSSYNA BACKEND — Sipariş Oluşturma

Akış (bkz. docs/architecture.md §6):
  POST /api/orders  → sipariş taslağı oluşturulur (status=pending)
  POST /api/payments/initiate → ödeme başlatılır
  webhook → ödeme onaylanınca orders.status=paid
"""
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import get_settings
from app.security import decode_token
from app.services.currency_service import get_latest_rate

router = APIRouter(prefix="/api/orders", tags=["Siparişler"])
settings = get_settings()
_optional_bearer = HTTPBearer(auto_error=False)

FREE_SHIPPING_THRESHOLD_TRY = 300.0
STANDARD_SHIPPING_COST_TRY = 49.9


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: Session = Depends(get_db),
) -> models.User | None:
    """Sipariş, giriş yapmamış (misafir) kullanıcılar tarafından da verilebilir."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials, settings.jwt_audience_customer)
    except HTTPException:
        return None
    return db.get(models.User, payload["sub"])


def _generate_order_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    # Demo amaçlı basit üretim: yıl + rastgele 6 haneli sayı + çakışma kontrolü.
    # Yüksek trafikli production'da PostgreSQL SEQUENCE kullanılması önerilir.
    for _ in range(5):
        candidate = f"MSY-{year}-{''.join(random.choices(string.digits, k=6))}"
        if not db.scalar(select(models.Order).where(models.Order.order_number == candidate)):
            return candidate
    raise RuntimeError("Sipariş numarası üretilemedi, lütfen tekrar deneyin.")


@router.post("", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: schemas.OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_optional_user),
):
    if not current_user and not payload.guest_email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Misafir siparişler için e-posta adresi zorunludur.")

    # --- Fiyatları SUNUCU tarafında, veritabanından oku — istemciden gelen fiyata ASLA güvenilmez ---
    order_items: list[models.OrderItem] = []
    subtotal = 0.0

    for line in payload.items:
        product = db.get(models.Product, line.product_id)
        if not product or not product.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Ürün bulunamadı: #{line.product_id}")
        if product.stock_quantity < line.quantity:
            raise HTTPException(status.HTTP_409_CONFLICT, f"'{product.name_tr}' için yeterli stok yok.")

        unit_price = float(product.price_try)

        # Kurumsal müşteri + miktar bazlı kademeli indirim (pricing_tiers)
        if current_user and current_user.role == "corporate":
            best_tier = max(
                (t for t in product.pricing_tiers if t.min_quantity <= line.quantity),
                key=lambda t: t.min_quantity,
                default=None,
            )
            if best_tier:
                unit_price = round(unit_price * (1 - float(best_tier.discount_percentage) / 100), 2)

        line_total = round(unit_price * line.quantity, 2)
        subtotal += line_total

        order_items.append(models.OrderItem(
            product_id=product.id,
            variant_id=line.variant_id,
            product_name_snapshot=product.name_tr,
            sku_snapshot=product.sku,
            quantity=line.quantity,
            unit_price=unit_price,
            total_price=line_total,
        ))
        product.stock_quantity -= line.quantity  # stok rezervasyonu (basit model — ödeme başarısız olursa iade edilmeli)

    # --- İndirim kodu ---
    discount_amount = 0.0
    applied_discount = None
    if payload.discount_code:
        applied_discount = db.scalar(
            select(models.Discount).where(models.Discount.code == payload.discount_code.upper(), models.Discount.is_active.is_(True))
        )
        if applied_discount and subtotal >= float(applied_discount.min_order_amount):
            if applied_discount.type == "percentage":
                discount_amount = round(subtotal * float(applied_discount.value) / 100, 2)
            else:
                discount_amount = min(float(applied_discount.value), subtotal)

            # Hoş geldin kuponu kullanıldıysa user_discounts.is_used=true işaretle
            if current_user:
                user_discount = db.scalar(
                    select(models.UserDiscount).where(
                        models.UserDiscount.user_id == current_user.id,
                        models.UserDiscount.discount_id == applied_discount.id,
                        models.UserDiscount.is_used.is_(False),
                    )
                )
                if user_discount:
                    user_discount.is_used = True
                    user_discount.used_at = datetime.now(timezone.utc)

    shipping_cost = 0.0 if (subtotal - discount_amount) >= FREE_SHIPPING_THRESHOLD_TRY else STANDARD_SHIPPING_COST_TRY
    total_amount = round(subtotal - discount_amount + shipping_cost, 2)

    # --- Fatura bilgisi ---
    billing_company = payload.billing.company_name if payload.billing.type == "corporate" else None
    billing_tax_office = payload.billing.tax_office if payload.billing.type == "corporate" else None
    billing_tax_number = payload.billing.tax_number if payload.billing.type == "corporate" else None

    # --- Teslimat adresi ---
    # Not: `addresses.user_id` şemada NOT NULL'dur (bkz. database/schema.sql),
    # bu yüzden yalnızca giriş yapmış kullanıcılar için kalıcı bir adres
    # kaydı oluşturup siparişe bağlıyoruz. Misafir siparişlerinde adres
    # bilgisi kalıcı olarak saklanmaz; production'a geçmeden önce ya
    # `addresses.user_id` nullable yapılmalı ya da misafir siparişler için
    # `orders` tablosuna ayrı bir "guest_shipping_snapshot" JSONB kolonu
    # eklenmelidir.
    shipping_address_id = None
    if current_user:
        shipping_address = models.Address(
            user_id=current_user.id,
            title="Sipariş Teslimat Adresi",
            full_name=payload.shipping.full_name,
            phone=payload.shipping.phone,
            city=payload.shipping.city,
            district=payload.shipping.district,
            postal_code=payload.shipping.postal_code,
            address_line=payload.shipping.address_line,
        )
        db.add(shipping_address)
        db.flush()
        shipping_address_id = shipping_address.id

    exchange_rate_used = None
    if payload.currency != "TRY":
        rate_row = get_latest_rate(db, payload.currency)
        exchange_rate_used = float(rate_row.rate_to_try) if rate_row else None

    order = models.Order(
        order_number=_generate_order_number(db),
        user_id=current_user.id if current_user else None,
        status="pending",
        shipping_address_id=shipping_address_id,
        billing_company_name=billing_company,
        billing_tax_office=billing_tax_office,
        billing_tax_number=billing_tax_number,
        subtotal=round(subtotal, 2),
        discount_amount=discount_amount,
        shipping_cost=shipping_cost,
        total_amount=total_amount,
        currency=payload.currency,
        exchange_rate_used=exchange_rate_used,
        applied_discount_id=applied_discount.id if applied_discount else None,
        customer_note=payload.customer_note,
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sipariş bulunamadı.")
    return order
