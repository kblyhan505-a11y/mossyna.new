# Mossyna E-Ticaret Platformu — Sistem Mimarisi

**Marka:** Mossyna (Ev Tekstili)
**Prensip:** Hiçbir hazır e-ticaret altyapısı (Shopify, WooCommerce/WordPress, vb.) kullanılmaz. Backend, veritabanı ve frontend sıfırdan, bağımsız olarak inşa edilir.

---

## 1. Teknoloji Seçimi ve Gerekçesi

| Katman | Teknoloji | Gerekçe |
|---|---|---|
| Backend API | **Python 3.12 + FastAPI** | Yüksek performans (async), otomatik OpenAPI/Swagger dokümantasyonu, Pydantic ile güçlü veri doğrulama, admin panel ve mobil app'e aynı API'den hizmet verilebilir. |
| ORM / Migration | **SQLAlchemy 2.0 + Alembic** | Tip güvenli sorgular, versiyonlanabilir şema göçleri (migration). |
| Veritabanı | **PostgreSQL 16** | İlişkisel bütünlük (foreign key), JSONB desteği (ör. ürün özellikleri), ölçeklenebilirlik, 200-350 ürün + sipariş hacmi için fazlasıyla yeterli. |
| Kimlik Doğrulama | **JWT (access + refresh token) + bcrypt** | Stateless auth, rol bazlı yetkilendirme (RBAC): `individual`, `corporate`, `admin`, `superadmin`. |
| Zamanlanmış Görevler | **APScheduler (veya Celery+Redis, ileri aşamada)** | Dolar kuru çekme işini günde birkaç kez otomatik tetiklemek için. |
| Frontend (Müşteri) | **Saf HTML5 + CSS3 + Vanilla JS (ES6+)** | Framework bağımlılığı yok, hızlı yüklenme, SEO dostu, bakımı kolay. `fetch()` ile REST API tüketimi. |
| Admin Panel | **Saf HTML/CSS/JS, ayrı `/admin` SPA-benzeri arayüz** | Kod dokunmadan yönetim; kendi JWT oturumu (rol=admin) ile korunur. |
| Ödeme | **Adapter Pattern**: `PaymentProviderInterface` → `PayTRProvider`, `StripeProvider` | Yurt içi kartlar için PayTR (Sanal POS), yurt dışı için Stripe. Tek arayüz üzerinden değiştirilebilir. |
| Dosya/Görsel Depolama | Yerelde `/media` klasörü (ileride S3/Cloudflare R2'ye taşınabilir) | Ürün görselleri için basit, taşınabilir çözüm. |
| Konteynerleştirme | **Docker Compose** (api, db, nginx, static frontend) | Tek komutla ayağa kalkan, taşınabilir ortam. |

> Not: İstek üzerine yapı hem FastAPI hem de Node.js/Express ile birebir uyumlu şekilde tasarlanmıştır (REST + JSON sözleşmesi framework'ten bağımsızdır). Kod örnekleri FastAPI/Python ile ilerleyecektir; istenirse Node.js/Express karşılığı da üretilebilir.

---

## 2. Klasör Yapısı

```
mossyna/
├── database/
│   └── schema.sql                # Aşama 1 — tam DDL (tablolar, ilişkiler, index'ler)
├── docs/
│   └── architecture.md           # Bu dosya
├── backend/                      # Aşama 5'te doldurulacak (FastAPI)
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── products.py
│   │   │   ├── cart.py
│   │   │   ├── orders.py
│   │   │   ├── payments.py
│   │   │   ├── exchange_rate.py
│   │   │   ├── contact.py
│   │   │   └── admin/
│   │   ├── services/
│   │   │   ├── payment_providers/
│   │   │   └── currency_service.py
│   │   └── core/ (config, security)
│   └── requirements.txt
├── frontend/                     # Aşama 2 — müşteri arayüzü
│   ├── index.html
│   ├── products.html
│   ├── checkout.html
│   ├── css/style.css
│   ├── js/
│   │   ├── i18n.js
│   │   ├── cart.js
│   │   └── main.js
│   └── assets/img/
└── admin/                        # Aşama 4 — yönetici paneli
    ├── index.html (dashboard)
    ├── products.html
    ├── orders.html
    ├── messages.html
    ├── exchange-rate.html
    ├── css/admin.css
    └── js/admin.js
```

---

## 3. Rol ve Yetkilendirme Mimarisi

- `users.role`: `individual` (bireysel) | `corporate` (kurumsal/B2B)
- Kurumsal kullanıcılar için `company_name`, `tax_office`, `tax_number` zorunlu alanlar; onay sonrası `is_verified_b2b = true` olur.
- Ürün fiyatlandırmasında iki katman vardır: `products.price_try` (bireysel liste fiyatı) ve `pricing_tiers` tablosu (kurumsal/miktar bazlı iskonto). Frontend, oturum rolüne göre doğru fiyatı gösterir.
- `admin_users` tablosu müşteri `users` tablosundan tamamen ayrıdır — admin oturumları farklı bir JWT `aud` (audience) claim'i ile imzalanır, böylece bir müşteri token'ı asla admin API'sinde geçerli olmaz.

## 4. Kampanya / Hoş Geldin İndirimi Akışı

1. Yeni kullanıcı kayıt olur → backend otomatik olarak `discounts` tablosunda tanımlı "WELCOME10" kuponunu `user_discounts` tablosuna kullanılmamış (`is_used = false`) olarak atar.
2. Frontend, giriş sonrası `/api/me/discounts` çağrısıyla kullanılmamış kuponu tespit eder ve hoş geldin bildirimini/banner'ını gösterir.
3. Sepet toplamı hesaplanırken kupon kodu otomatik ya da manuel uygulanabilir; `orders.discount_amount` alanına yazılır.

## 5. Çoklu Para Birimi ve Dolar Kuru Mimarisi

- `exchange_rates` tablosu her gün (veya günde birkaç kez) TCMB/harici API'den çekilen `USD→TRY` ve `EUR→TRY` kurlarını saklar.
- Ürünlerin maliyet/baz fiyatı `base_price_usd` alanında tutulur; admin panelindeki "Kur Güncelle" butonu veya otomatik zamanlanmış görev, `price_try = base_price_usd * rate * (1 + admin_margin)` formülüyle tüm aktif ürünlerin TL fiyatını yeniden hesaplar. Admin isterse ürün bazında manuel override yapabilir (`price_override = true`).
- Checkout sayfasında müşteri TL / USD / EUR arasında görüntüleme para birimini değiştirebilir (ödeme yine de tek bir taban para biriminde — TL — tahsil edilir, karşılık gelen döviz tutarı bilgilendirme amaçlıdır; yurt dışı Stripe ödemelerinde gerçek tahsilat USD/EUR olabilir).

## 6. Ödeme Mimarisi (Özet — detay Aşama 5'te)

```
Checkout → POST /api/orders (sipariş taslağı oluşturulur, status=pending)
         → POST /api/payments/initiate (provider seçimine göre PayTR iFrame token
           ya da Stripe PaymentIntent oluşturulur)
         → Kullanıcı ödemeyi tamamlar
         → Provider webhook'u → POST /api/payments/webhook/{provider}
         → payments.status = success/failed güncellenir → orders.status = paid
         → E-posta / admin panel bildirimi tetiklenir
```

## 7. İletişim / Mesaj Sistemi

- Site üzerindeki İletişim Formu → `POST /api/contact` → `contact_messages` tablosuna `status=new` ile yazılır.
- Admin panelinde `messages.html` bu kayıtları listeler; admin cevap yazdığında `admin_reply` alanı doldurulur, `status=replied` olur ve (ileride) kullanıcıya e-posta gönderilir.

## 8. Sonraki Aşamalar

- **Aşama 3:** Bireysel/Kurumsal üyelik giriş-kayıt ekranları (HTML/CSS/JS + auth akışı).
- **Aşama 4:** `/admin` paneli — ürün/stok/fiyat yönetimi, kur modülü arayüzü, mesaj yönetimi.
- **Aşama 5:** FastAPI backend kodu — modeller, router'lar, kur çekme servisi, ödeme adaptörleri.
