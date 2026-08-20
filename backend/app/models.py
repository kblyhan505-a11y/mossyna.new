"""
MOSSYNA BACKEND — SQLAlchemy ORM Modelleri

Bu dosya `database/schema.sql` ile birebir uyumludur. Gerçek bir migration
akışı için Alembic kullanılmalıdır (`alembic revision --autogenerate`);
bu dosya doğrudan modelleri, schema.sql ise "source of truth" DDL'i temsil
eder.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Text, Integer, SmallInteger, Numeric, Boolean, DateTime,
    ForeignKey, Enum, UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------
# 1. KULLANICILAR
# ---------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # Google ile giriş yapan kullanıcıların şifresi olmaz — bu yüzden nullable.
    # auth_provider: "email" (klasik kayıt) | "google" (yalnızca Google ile) —
    # bir e-posta her iki yöntemle de doğrulanabilir (bkz. routers/auth.py POST /api/auth/google).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(Enum("individual", "corporate", name="user_role"), default="individual")
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    auth_provider: Mapped[str] = mapped_column(String(20), default="email")

    company_name: Mapped[str | None] = mapped_column(String(255))
    tax_office: Mapped[str | None] = mapped_column(String(120))
    tax_number: Mapped[str | None] = mapped_column(String(30))
    is_verified_b2b: Mapped[bool] = mapped_column(Boolean, default=False)

    preferred_language: Mapped[str] = mapped_column(String(5), default="tr")
    preferred_currency: Mapped[str] = mapped_column(String(5), default="TRY")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    country: Mapped[str] = mapped_column(String(80), default="Türkiye")
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(20))
    address_line: Mapped[str] = mapped_column(Text, nullable=False)
    is_default_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default_billing: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="addresses")


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(Enum("admin", "superadmin", "support", name="admin_role"), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------
# 2. KATEGORİLER VE ÜRÜNLER
# ---------------------------------------------------------------------

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name_tr: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    name_tr: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(280), unique=True, nullable=False)
    short_desc_tr: Mapped[str | None] = mapped_column(String(500))
    short_desc_en: Mapped[str | None] = mapped_column(String(500))
    description_tr: Mapped[str | None] = mapped_column(Text)
    description_en: Mapped[str | None] = mapped_column(Text)
    material_info_tr: Mapped[str | None] = mapped_column(Text)
    material_info_en: Mapped[str | None] = mapped_column(Text)
    # Shopify mağazasındaki karşılık gelen ürün varyantının Global ID'si
    # (ör. "gid://shopify/ProductVariant/12345678"). Ödeme, Shopify'ın barındırdığı
    # checkout sayfasına yönlendirilerek tamamlanır (bkz. services/payment_providers/
    # shopify_provider.py) — bu alan boşsa o ürün sepete eklenip ödemeye geçildiğinde
    # açıklayıcı bir hata verilir.
    shopify_variant_id: Mapped[str | None] = mapped_column(String(120))

    base_price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    margin_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=40.00)
    price_try: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    price_override: Mapped[bool] = mapped_column(Boolean, default=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(10, 2))

    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_b2b_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category: Mapped["Category | None"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.sort_order"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    pricing_tiers: Mapped[list["PricingTier"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    translations: Mapped[list["ProductTranslation"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductTranslation.language_code"
    )

    # --- Sadece okunabilir yardımcı alanlar (API yanıtlarında kullanılır) ---
    @property
    def category_slug(self) -> str | None:
        return self.category.slug if self.category else None

    @property
    def primary_image_url(self) -> str | None:
        if not self.images:
            return None
        primary = next((img for img in self.images if img.is_primary), None)
        return (primary or self.images[0]).image_url


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text_tr: Mapped[str | None] = mapped_column(String(255))
    alt_text_en: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    variant_sku: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name_tr: Mapped[str] = mapped_column(String(150), nullable=False)
    name_en: Mapped[str] = mapped_column(String(150), nullable=False)
    price_modifier: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped["Product"] = relationship(back_populates="variants")


class PricingTier(Base):
    __tablename__ = "pricing_tiers"
    __table_args__ = (UniqueConstraint("product_id", "min_quantity"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="pricing_tiers")


class ProductTranslation(Base):
    """
    Türkçe (name_tr/description_tr) ve İngilizce (name_en/description_en) doğrudan
    `products` tablosunda kolon olarak tutulur (en sık kullanılan iki dil olduğu
    için sorgu/indeksleme açısından pratik). Admin panelindeki dördüncü ve sonraki
    diller (DE/FR/RU/AR) ise bu ayrı çeviri tablosunda satır satır tutulur — bkz.
    admin/products.html dil sekmeleri ve routers/products.py çeviri upsert mantığı.
    """
    __tablename__ = "product_translations"
    __table_args__ = (UniqueConstraint("product_id", "language_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    language_code: Mapped[str] = mapped_column(String(5), nullable=False)  # "de" | "fr" | "ru" | "ar"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_desc: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship(back_populates="translations")


# ---------------------------------------------------------------------
# 3. KAMPANYA / İNDİRİM
# ---------------------------------------------------------------------

class Discount(Base):
    __tablename__ = "discounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description_tr: Mapped[str | None] = mapped_column(String(255))
    description_en: Mapped[str | None] = mapped_column(String(255))
    type: Mapped[str] = mapped_column(Enum("percentage", "fixed_amount", name="discount_type"), default="percentage")
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    min_order_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_auto_welcome: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_limit_per_user: Mapped[int] = mapped_column(Integer, default=1)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserDiscount(Base):
    __tablename__ = "user_discounts"
    __table_args__ = (UniqueConstraint("user_id", "discount_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    discount_id: Mapped[int] = mapped_column(ForeignKey("discounts.id", ondelete="CASCADE"))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------
# 4. SİPARİŞLER VE ÖDEMELER
# ---------------------------------------------------------------------

ORDER_STATUSES = (
    "pending", "awaiting_payment", "paid", "processing",
    "shipped", "delivered", "cancelled", "refunded",
)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(Enum(*ORDER_STATUSES, name="order_status"), default="pending")

    shipping_address_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("addresses.id"))
    billing_address_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("addresses.id"))

    billing_company_name: Mapped[str | None] = mapped_column(String(255))
    billing_tax_office: Mapped[str | None] = mapped_column(String(120))
    billing_tax_number: Mapped[str | None] = mapped_column(String(30))

    subtotal: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    currency: Mapped[str] = mapped_column(String(5), default="TRY")
    exchange_rate_used: Mapped[float | None] = mapped_column(Numeric(10, 4))

    payment_method: Mapped[str | None] = mapped_column(String(30))
    payment_provider: Mapped[str | None] = mapped_column(String(30))
    applied_discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id"))

    customer_note: Mapped[str | None] = mapped_column(Text)
    admin_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User | None"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    product_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    sku_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    # Ürün sonradan silinmiş olabileceği için None olabilir. Shopify ödeme
    # sağlayıcısı, sipariş kalemini Shopify ürün varyantına eşlemek için bunu kullanır
    # (bkz. services/payment_providers/shopify_provider.py).
    product: Mapped["Product | None"] = relationship()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    order_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("orders.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    provider_txn_id: Mapped[str | None] = mapped_column(String(150))
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(Enum("initiated", "success", "failed", "refunded", name="payment_status"), default="initiated")
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    order: Mapped["Order"] = relationship(back_populates="payments")


# ---------------------------------------------------------------------
# 5. DÖVİZ KURU
# ---------------------------------------------------------------------

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency_code: Mapped[str] = mapped_column(String(5), nullable=False)
    rate_to_try: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="TCMB")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------
# 6. İLETİŞİM
# ---------------------------------------------------------------------

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    subject: Mapped[str | None] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Enum("new", "read", "replied", "closed", name="message_status"), default="new")
    admin_reply: Mapped[str | None] = mapped_column(Text)
    replied_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------
# 7. YORUMLAR VE DENETİM
# ---------------------------------------------------------------------

class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"))
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("admin_users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(60))
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------
# 8. HAKKIMIZDA (ÜRETİM TESİSİ FOTOĞRAFLARI)
# ---------------------------------------------------------------------

class AboutUsPhoto(Base):
    """Ana sayfadaki '#about' bölümünde gösterilen üretim tesisi fotoğrafları.
    Admin panelindeki hakkimizda.html'de yönetilir; sırası sort_order'a göredir."""
    __tablename__ = "about_us_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    caption_tr: Mapped[str | None] = mapped_column(String(255))
    caption_en: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
