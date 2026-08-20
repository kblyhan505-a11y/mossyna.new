"""
MOSSYNA BACKEND — Pydantic Şemaları (Request / Response modelleri)
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# =====================================================================
# AUTH
# =====================================================================

class CustomerRegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=5, max_length=30)
    password: str = Field(min_length=6, max_length=128)
    role: Literal["individual", "corporate"] = "individual"
    company_name: Optional[str] = None
    tax_office: Optional[str] = None
    tax_number: Optional[str] = None

    @field_validator("company_name", "tax_office", "tax_number")
    @classmethod
    def corporate_fields_required(cls, v, info):
        # Not: Basit alan bazlı kontrol; rol=corporate iken bu alanların dolu
        # olduğu asıl doğrulama router içinde (tüm alanlara erişimle) yapılır.
        return v


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    company_name: Optional[str] = None
    is_verified_b2b: bool

    model_config = {"from_attributes": True}


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}


class GoogleAuthRequest(BaseModel):
    # Google Identity Services'in tarayıcıda ürettiği kimlik doğrulama JWT'si
    # (bkz. frontend/js/auth-google.js — `response.credential`). Backend bunu
    # Google'ın genel anahtarlarıyla doğrular, kendi imzalı token'ını üretmez.
    credential: str = Field(min_length=10)


# =====================================================================
# ÜRÜNLER
# =====================================================================

class ProductImageResponse(BaseModel):
    id: int
    image_url: str
    is_primary: bool

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    id: int
    slug: str
    name_tr: str
    name_en: str
    image_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductTranslationItem(BaseModel):
    """DE/FR/RU/AR çevirisi — bkz. models.ProductTranslation."""
    language_code: str
    name: str
    short_desc: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ProductTranslationInput(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    short_desc: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = None


class ProductListItem(BaseModel):
    id: int
    sku: str
    name_tr: str
    name_en: str
    slug: str
    short_desc_tr: Optional[str] = None
    short_desc_en: Optional[str] = None
    description_tr: Optional[str] = None
    description_en: Optional[str] = None
    shopify_variant_id: Optional[str] = None
    translations: list[ProductTranslationItem] = []
    category_id: Optional[int] = None
    category_slug: Optional[str] = None
    price_try: float
    base_price_usd: float
    margin_percentage: float
    compare_at_price: Optional[float] = None
    stock_quantity: int
    low_stock_threshold: int
    is_active: bool
    is_featured: bool
    is_b2b_available: bool
    price_override: bool
    primary_image_url: Optional[str] = None
    images: list[ProductImageResponse] = []

    model_config = {"from_attributes": True}


class AdminProductListResponse(BaseModel):
    items: list[ProductListItem]
    total: int


class ProductCreateRequest(BaseModel):
    sku: str
    category_id: Optional[int] = None
    name_tr: str
    name_en: str
    short_desc_tr: Optional[str] = Field(default=None, max_length=500)
    short_desc_en: Optional[str] = Field(default=None, max_length=500)
    description_tr: Optional[str] = None
    description_en: Optional[str] = None
    shopify_variant_id: Optional[str] = Field(default=None, max_length=120)
    # Anahtar = dil kodu ("de" | "fr" | "ru" | "ar"); bkz. ProductTranslation.
    translations: Optional[dict[str, ProductTranslationInput]] = None
    base_price_usd: float = Field(gt=0)
    margin_percentage: float = Field(default=40.0, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    is_active: bool = True
    is_featured: bool = False
    is_b2b_available: bool = True


class ProductUpdateRequest(BaseModel):
    name_tr: Optional[str] = None
    name_en: Optional[str] = None
    short_desc_tr: Optional[str] = Field(default=None, max_length=500)
    short_desc_en: Optional[str] = Field(default=None, max_length=500)
    description_tr: Optional[str] = None
    description_en: Optional[str] = None
    shopify_variant_id: Optional[str] = Field(default=None, max_length=120)
    translations: Optional[dict[str, ProductTranslationInput]] = None
    category_id: Optional[int] = None
    base_price_usd: Optional[float] = Field(default=None, gt=0)
    margin_percentage: Optional[float] = Field(default=None, ge=0)
    price_override: Optional[bool] = None
    price_try: Optional[float] = Field(default=None, gt=0)  # price_override=true iken manuel fiyat
    stock_quantity: Optional[int] = Field(default=None, ge=0)
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_b2b_available: Optional[bool] = None


# =====================================================================
# SİPARİŞ
# =====================================================================

class OrderItemRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(gt=0, le=999)


class BillingInfo(BaseModel):
    type: Literal["individual", "corporate"] = "individual"
    company_name: Optional[str] = None
    tax_office: Optional[str] = None
    tax_number: Optional[str] = None


class ShippingInfo(BaseModel):
    full_name: str
    phone: str
    city: str
    district: str
    address_line: str
    postal_code: Optional[str] = None


class OrderCreateRequest(BaseModel):
    items: list[OrderItemRequest] = Field(min_length=1)
    shipping: ShippingInfo
    billing: BillingInfo
    currency: Literal["TRY", "USD", "EUR"] = "TRY"
    discount_code: Optional[str] = None
    customer_note: Optional[str] = None
    # Misafir (giriş yapmamış) siparişler için — gerçek sistemde e-posta doğrulaması eklenir
    guest_email: Optional[EmailStr] = None


class OrderItemResponse(BaseModel):
    product_name_snapshot: str
    sku_snapshot: str
    quantity: int
    unit_price: float
    total_price: float

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: str
    order_number: str
    status: str
    subtotal: float
    discount_amount: float
    shipping_cost: float
    total_amount: float
    currency: str
    items: list[OrderItemResponse]

    model_config = {"from_attributes": True}


# =====================================================================
# ÖDEME
# =====================================================================

class PaymentInitiateRequest(BaseModel):
    order_id: str
    provider: Literal["shopify", "paytr", "stripe", "bank_transfer"]


class PaymentInitiateResponse(BaseModel):
    payment_id: str
    provider: str
    status: str
    # Sağlayıcıya göre bu alanlardan yalnızca biri dolu olur.
    shopify_checkout_url: Optional[str] = None
    paytr_iframe_token: Optional[str] = None
    stripe_client_secret: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    bank_transfer_iban: Optional[str] = None


# =====================================================================
# DÖVİZ KURU
# =====================================================================

class ExchangeRateResponse(BaseModel):
    currency_code: str
    rate_to_try: float
    source: str
    fetched_at: datetime

    model_config = {"from_attributes": True}


class ExchangeRateRefreshResponse(BaseModel):
    usd_rate: float
    eur_rate: float
    source: str
    products_updated: int
    average_price_change_percent: float


class ManualRateRequest(BaseModel):
    usd_rate: float = Field(gt=0)
    eur_rate: float = Field(gt=0)


# =====================================================================
# İLETİŞİM
# =====================================================================

class ContactMessageCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: Optional[str] = None
    subject: Optional[str] = None
    message: str = Field(min_length=1)


class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    subject: Optional[str] = None
    message: str
    status: str
    admin_reply: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ContactReplyRequest(BaseModel):
    reply: str = Field(min_length=1)


# =====================================================================
# HAKKIMIZDA (ÜRETİM TESİSİ FOTOĞRAFLARI)
# =====================================================================

class AboutUsPhotoResponse(BaseModel):
    id: int
    image_url: str
    caption_tr: Optional[str] = None
    caption_en: Optional[str] = None
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AboutUsPhotoUpdateRequest(BaseModel):
    caption_tr: Optional[str] = Field(default=None, max_length=255)
    caption_en: Optional[str] = Field(default=None, max_length=255)
    sort_order: Optional[int] = None
