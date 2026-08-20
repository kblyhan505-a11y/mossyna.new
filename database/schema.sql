-- =====================================================================
-- MOSSYNA E-TİCARET PLATFORMU — VERİTABANI ŞEMASI (PostgreSQL 16)
-- Aşama 1 teslimatı
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------
-- 1. KULLANICILAR VE ROLLER
-- ---------------------------------------------------------------------

CREATE TYPE user_role AS ENUM ('individual', 'corporate');

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    phone               VARCHAR(30),
    role                user_role NOT NULL DEFAULT 'individual',
    -- Kurumsal (B2B) alanları
    company_name        VARCHAR(255),
    tax_office          VARCHAR(120),
    tax_number          VARCHAR(30),
    is_verified_b2b      BOOLEAN NOT NULL DEFAULT FALSE,
    -- Genel
    preferred_language  VARCHAR(5) NOT NULL DEFAULT 'tr',   -- 'tr' | 'en'
    preferred_currency  VARCHAR(5) NOT NULL DEFAULT 'TRY',  -- 'TRY' | 'USD' | 'EUR'
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified_at   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_role ON users(role);

CREATE TABLE addresses (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title               VARCHAR(80) NOT NULL,           -- "Ev", "Ofis" vb.
    full_name           VARCHAR(150) NOT NULL,
    phone               VARCHAR(30) NOT NULL,
    country             VARCHAR(80) NOT NULL DEFAULT 'Türkiye',
    city                VARCHAR(80) NOT NULL,
    district            VARCHAR(80) NOT NULL,
    postal_code         VARCHAR(20),
    address_line        TEXT NOT NULL,
    is_default_shipping BOOLEAN NOT NULL DEFAULT FALSE,
    is_default_billing  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_addresses_user ON addresses(user_id);

-- Admin kullanıcıları müşteri tablosundan tamamen ayrı tutulur (güvenlik)
CREATE TYPE admin_role AS ENUM ('admin', 'superadmin', 'support');

CREATE TABLE admin_users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username      VARCHAR(80) NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          admin_role NOT NULL DEFAULT 'admin',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- 2. KATEGORİLER VE ÜRÜNLER
-- ---------------------------------------------------------------------

CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name_tr     VARCHAR(150) NOT NULL,
    name_en     VARCHAR(150) NOT NULL,
    slug        VARCHAR(160) NOT NULL UNIQUE,
    image_url   VARCHAR(500),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE products (
    id                 SERIAL PRIMARY KEY,
    sku                VARCHAR(60) NOT NULL UNIQUE,
    category_id        INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    name_tr            VARCHAR(255) NOT NULL,
    name_en            VARCHAR(255) NOT NULL,
    slug               VARCHAR(280) NOT NULL UNIQUE,
    short_desc_tr      VARCHAR(500),
    short_desc_en      VARCHAR(500),
    description_tr     TEXT,
    description_en     TEXT,
    material_info_tr   TEXT,                     -- kumaş/dolgu bilgisi (%100 pamuk vb.)
    material_info_en   TEXT,

    -- Fiyatlandırma
    base_price_usd     NUMERIC(10,2) NOT NULL,     -- Dolar bazlı maliyet/baz fiyat
    margin_percentage  NUMERIC(5,2)  NOT NULL DEFAULT 40.00,  -- kâr marjı
    price_try          NUMERIC(10,2) NOT NULL,     -- otomatik/hesaplanan bireysel satış fiyatı (TL)
    price_override     BOOLEAN NOT NULL DEFAULT FALSE, -- true ise otomatik kur güncellemesi bu üründe fiyatı değiştirmez
    compare_at_price   NUMERIC(10,2),               -- "eski fiyat" (indirim gösterimi için)

    stock_quantity     INTEGER NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER NOT NULL DEFAULT 5,

    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    is_b2b_available   BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured        BOOLEAN NOT NULL DEFAULT FALSE,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_products_featured ON products(is_featured);

CREATE TABLE product_images (
    id          SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    image_url   VARCHAR(500) NOT NULL,
    alt_text_tr VARCHAR(255),
    alt_text_en VARCHAR(255),
    is_primary  BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_product_images_product ON product_images(product_id);

-- Renk / ebat gibi varyasyonlar
CREATE TABLE product_variants (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_sku     VARCHAR(80) NOT NULL UNIQUE,
    name_tr         VARCHAR(150) NOT NULL,   -- örn. "Bej / 150x200"
    name_en         VARCHAR(150) NOT NULL,
    price_modifier  NUMERIC(10,2) NOT NULL DEFAULT 0, -- ana fiyata eklenen/çıkarılan tutar
    stock_quantity  INTEGER NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_variants_product ON product_variants(product_id);

-- Kurumsal (B2B) miktar bazlı iskonto kademeleri
CREATE TABLE pricing_tiers (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    min_quantity    INTEGER NOT NULL,
    discount_percentage NUMERIC(5,2) NOT NULL,  -- örn. 15.00 => %15 indirim
    UNIQUE(product_id, min_quantity)
);

-- ---------------------------------------------------------------------
-- 3. KAMPANYA / İNDİRİM KUPONLARI
-- ---------------------------------------------------------------------

CREATE TYPE discount_type AS ENUM ('percentage', 'fixed_amount');

CREATE TABLE discounts (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(50) NOT NULL UNIQUE,   -- "WELCOME10"
    description_tr      VARCHAR(255),
    description_en      VARCHAR(255),
    type                discount_type NOT NULL DEFAULT 'percentage',
    value               NUMERIC(10,2) NOT NULL,
    min_order_amount    NUMERIC(10,2) NOT NULL DEFAULT 0,
    is_auto_welcome     BOOLEAN NOT NULL DEFAULT FALSE, -- yeni üyelere otomatik atanır mı
    usage_limit_per_user INTEGER NOT NULL DEFAULT 1,
    valid_from          TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to            TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE user_discounts (
    id           SERIAL PRIMARY KEY,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    discount_id  INTEGER NOT NULL REFERENCES discounts(id) ON DELETE CASCADE,
    is_used      BOOLEAN NOT NULL DEFAULT FALSE,
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at      TIMESTAMPTZ,
    UNIQUE(user_id, discount_id)
);

-- ---------------------------------------------------------------------
-- 4. SEPET
-- ---------------------------------------------------------------------

CREATE TABLE carts (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL = misafir (session_id ile takip)
    session_id   VARCHAR(120),
    currency     VARCHAR(5) NOT NULL DEFAULT 'TRY',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (
    id           SERIAL PRIMARY KEY,
    cart_id      UUID NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    variant_id   INTEGER REFERENCES product_variants(id),
    quantity     INTEGER NOT NULL CHECK (quantity > 0),
    unit_price   NUMERIC(10,2) NOT NULL,  -- ekleme anındaki fiyat (snapshot)
    added_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cart_items_cart ON cart_items(cart_id);

-- ---------------------------------------------------------------------
-- 5. SİPARİŞLER VE ÖDEMELER
-- ---------------------------------------------------------------------

CREATE TYPE order_status AS ENUM (
    'pending', 'awaiting_payment', 'paid', 'processing',
    'shipped', 'delivered', 'cancelled', 'refunded'
);

CREATE TABLE orders (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number      VARCHAR(30) NOT NULL UNIQUE,  -- "MSY-2026-000123"
    user_id           UUID REFERENCES users(id),
    status            order_status NOT NULL DEFAULT 'pending',

    shipping_address_id UUID REFERENCES addresses(id),
    billing_address_id  UUID REFERENCES addresses(id),

    -- Kurumsal fatura bilgisi (adres tablosundan bağımsız, sipariş anı için sabitlenir)
    billing_company_name VARCHAR(255),
    billing_tax_office    VARCHAR(120),
    billing_tax_number    VARCHAR(30),

    subtotal          NUMERIC(10,2) NOT NULL,
    discount_amount   NUMERIC(10,2) NOT NULL DEFAULT 0,
    shipping_cost     NUMERIC(10,2) NOT NULL DEFAULT 0,
    tax_amount        NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_amount      NUMERIC(10,2) NOT NULL,

    currency          VARCHAR(5) NOT NULL DEFAULT 'TRY',
    exchange_rate_used NUMERIC(10,4),               -- ödeme anındaki kur (yurt dışı için)

    payment_method    VARCHAR(30),                  -- 'credit_card' | 'bank_transfer'
    payment_provider  VARCHAR(30),                  -- 'paytr' | 'stripe'

    applied_discount_id INTEGER REFERENCES discounts(id),

    customer_note     TEXT,
    admin_note        TEXT,

    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);

CREATE TABLE order_items (
    id                SERIAL PRIMARY KEY,
    order_id          UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id        INTEGER REFERENCES products(id),
    variant_id        INTEGER REFERENCES product_variants(id),
    product_name_snapshot VARCHAR(255) NOT NULL,   -- sipariş anındaki isim (ürün sonradan değişse de bozulmaz)
    sku_snapshot      VARCHAR(80) NOT NULL,
    quantity          INTEGER NOT NULL CHECK (quantity > 0),
    unit_price        NUMERIC(10,2) NOT NULL,
    total_price       NUMERIC(10,2) NOT NULL
);

CREATE INDEX idx_order_items_order ON order_items(order_id);

CREATE TYPE payment_status AS ENUM ('initiated', 'success', 'failed', 'refunded');

CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    provider        VARCHAR(30) NOT NULL,          -- 'paytr' | 'stripe' | 'bank_transfer'
    provider_txn_id VARCHAR(150),
    amount          NUMERIC(10,2) NOT NULL,
    currency        VARCHAR(5) NOT NULL,
    status          payment_status NOT NULL DEFAULT 'initiated',
    raw_response    JSONB,                          -- provider'dan dönen ham cevap (webhook debug için)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payments_order ON payments(order_id);

-- ---------------------------------------------------------------------
-- 6. DÖVİZ KURU MODÜLÜ
-- ---------------------------------------------------------------------

CREATE TABLE exchange_rates (
    id           SERIAL PRIMARY KEY,
    currency_code VARCHAR(5) NOT NULL,   -- 'USD' | 'EUR'
    rate_to_try  NUMERIC(10,4) NOT NULL,
    source       VARCHAR(50) NOT NULL DEFAULT 'TCMB',
    fetched_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_exchange_rates_currency_date ON exchange_rates(currency_code, fetched_at DESC);

-- ---------------------------------------------------------------------
-- 7. İLETİŞİM / MESAJ SİSTEMİ
-- ---------------------------------------------------------------------

CREATE TYPE message_status AS ENUM ('new', 'read', 'replied', 'closed');

CREATE TABLE contact_messages (
    id           SERIAL PRIMARY KEY,
    user_id      UUID REFERENCES users(id),   -- giriş yapmış kullanıcıysa
    name         VARCHAR(150) NOT NULL,
    email        VARCHAR(255) NOT NULL,
    phone        VARCHAR(30),
    subject      VARCHAR(255),
    message      TEXT NOT NULL,
    status       message_status NOT NULL DEFAULT 'new',
    admin_reply  TEXT,
    replied_by   UUID REFERENCES admin_users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    replied_at   TIMESTAMPTZ
);

CREATE INDEX idx_contact_messages_status ON contact_messages(status);

-- ---------------------------------------------------------------------
-- 8. ÜRÜN YORUMLARI (opsiyonel / gelecek genişleme)
-- ---------------------------------------------------------------------

CREATE TABLE reviews (
    id           SERIAL PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating       SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment      TEXT,
    is_approved  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reviews_product ON reviews(product_id);

-- ---------------------------------------------------------------------
-- 9. DENETİM KAYITLARI (admin işlemleri için audit log)
-- ---------------------------------------------------------------------

CREATE TABLE audit_logs (
    id           BIGSERIAL PRIMARY KEY,
    admin_id     UUID REFERENCES admin_users(id),
    action       VARCHAR(100) NOT NULL,   -- 'product.update', 'price.bulk_update' vb.
    entity_type  VARCHAR(60),
    entity_id    VARCHAR(60),
    details      JSONB,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- İLİŞKİ ÖZETİ
-- =====================================================================
-- users            1---N addresses
-- users            1---N orders
-- users            1---N user_discounts   N---1 discounts
-- categories       1---N categories (self, parent_id)
-- categories       1---N products
-- products         1---N product_images
-- products         1---N product_variants
-- products         1---N pricing_tiers
-- products         1---N reviews
-- carts            1---N cart_items       N---1 products/variants
-- orders           1---N order_items      N---1 products/variants (snapshot alanlarla)
-- orders           1---N payments
-- admin_users      1---N contact_messages (replied_by)
-- admin_users      1---N audit_logs
-- =====================================================================
