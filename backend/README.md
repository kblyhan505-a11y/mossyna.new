# Mossyna Backend (FastAPI)

Bu klasör, Aşama 5 kapsamında teslim edilen backend kodudur: döviz kuru
çekme servisi ve PayTR/Stripe ödeme entegrasyonu ile birlikte, önceki
aşamalardaki frontend (`frontend/`) ve admin panelin (`admin/`) ihtiyaç
duyduğu tüm REST API uçları.

## Kurulum

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# .env dosyasını gerçek veritabanı/PayTR/Stripe bilgilerinizle doldurun

# PostgreSQL veritabanınızı oluşturun, sonra:
python -m app.scripts.seed    # ilk admin hesabı + WELCOME10 kuponu + başlangıç kuru

uvicorn app.main:app --reload --port 8000
```

API dokümantasyonu: `http://localhost:8000/docs`

## Klasör Yapısı

```
backend/
├── app/
│   ├── main.py                 # FastAPI giriş noktası, router bağlama, CORS, lifespan
│   ├── config.py                # .env okuyan tip güvenli ayarlar (Pydantic Settings)
│   ├── database.py              # SQLAlchemy engine/session
│   ├── security.py              # JWT (müşteri/admin ayrı audience) + bcrypt
│   ├── models.py                # database/schema.sql ile birebir uyumlu ORM modelleri
│   ├── schemas.py                # Pydantic request/response şemaları
│   ├── routers/
│   │   ├── auth.py              # Bireysel/Kurumsal müşteri kayıt-giriş
│   │   ├── admin_auth.py         # Yönetici girişi (ayrı JWT audience)
│   │   ├── products.py           # Public ürün listeleme + Admin ürün CRUD
│   │   ├── orders.py             # Sipariş oluşturma (sunucu taraflı fiyatlandırma)
│   │   ├── payments.py           # Ödeme başlatma + PayTR/Stripe webhook'ları
│   │   ├── exchange_rate.py      # Güncel kur + Admin kur yenileme/manuel giriş
│   │   └── contact.py            # İletişim formu + Admin mesaj yönetimi
│   ├── services/
│   │   ├── currency_service.py    # TCMB/yedek API'den kur çekme + fiyat yeniden hesaplama
│   │   ├── scheduler.py           # APScheduler ile günlük otomatik kur güncelleme
│   │   └── payment_providers/
│   │       ├── base.py            # Ortak PaymentProvider arayüzü (adapter pattern)
│   │       ├── paytr_provider.py   # PayTR iFrame API (HMAC-SHA256 imzalama)
│   │       └── stripe_provider.py  # Stripe PaymentIntent + webhook doğrulama
│   └── scripts/
│       └── seed.py                # İlk admin hesabı + WELCOME10 kuponu + başlangıç kuru
└── requirements.txt
```

## Önemli Mimari Kararlar

- **Fiyat güvenliği:** `POST /api/orders` asla istemciden gelen fiyata güvenmez;
  her satır kalemi veritabanındaki güncel `price_try` üzerinden sunucuda hesaplanır.
- **Admin/Müşteri ayrımı:** İki farklı JWT `aud` (audience) claim'i kullanılır
  (`mossyna-customer` / `mossyna-admin`). Sızmış bir müşteri token'ı asla admin
  uçlarında kabul edilmez.
- **Ödeme sağlayıcı soyutlaması:** `services/payment_providers/base.py`'deki
  `PaymentProvider` arayüzü sayesinde yeni bir sağlayıcı (ör. Iyzico) eklemek
  yalnızca bu arayüzü uygulayan yeni bir sınıf yazmayı gerektirir —
  `routers/payments.py` hangi sağlayıcı olduğunu bilmez.
- **Kur güncelleme:** Hem admin panelindeki "Kuru Şimdi Güncelle" butonu hem de
  günlük zamanlanmış görev (varsayılan 09:00, `.env`'den ayarlanabilir) aynı
  `refresh_exchange_rates()` fonksiyonunu çağırır — tek bir doğruluk kaynağı.

## Bilinen Sınırlamalar (Production Öncesi Yapılacaklar)

- Alembic migration dosyaları henüz oluşturulmadı (`Base.metadata.create_all`
  yalnızca geliştirme ortamı içindir).
- Misafir (giriş yapmamış) sipariş akışında teslimat adresi kalıcı olarak
  saklanmaz (bkz. `routers/orders.py` içindeki ilgili yorum) — production'a
  geçmeden önce `addresses.user_id` nullable yapılmalı veya siparişe bağlı
  ayrı bir "guest shipping snapshot" alanı eklenmelidir.
- E-posta bildirimleri (sipariş onayı, mesaj yanıtı vb.) entegre değildir;
  bir e-posta servisi (SES/SendGrid) ve arka plan kuyruğu (Celery/RQ) eklenmelidir.
- Stok rezervasyonu basit tutulmuştur (sipariş oluşturulunca direkt düşülür);
  ödeme başarısız olursa stok iade akışı eklenmelidir.
